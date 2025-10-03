from typing import List, Tuple, Union, Optional
from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo.errors import BulkWriteError
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase as AsyncDatabase
from schema import TextNodeSchema, SymbolSchema, ChunkCreateSchema, ChunkUpdateSchema
from pydantic import ValidationError

class Database:
    def __init__(self, url: str, db_name: str = "metta_db") -> None:
        self.client: AsyncMongoClient = AsyncMongoClient(url)
        self.db: AsyncDatabase = self.client.get_database(db_name)

        # get collections
        self.text_nodes: AsyncCollection[TextNodeSchema] = self.db["text_nodes"]
        self.symbols: AsyncCollection[SymbolSchema] = self.db["symbols"]
        self.chunks_collection: AsyncCollection[ChunkCreateSchema] = self.db["chunks"]

    async def clear_text_nodes_symbols(self) -> None:
        """
        clear these collections after a function scope is processed
        to avoid duplicate key errors on processing same function names 
        in different scopes
        """
        await self.text_nodes.delete_many({})
        await self.symbols.delete_many({})
    
    async def clear_all_collections(self) -> None:
        """Clear all collections development only."""
        await self.text_nodes.delete_many({})
        await self.symbols.delete_many({})
        await self.chunks_collection.delete_many({})

    async def close(self) -> None:
        await self.client.close()
    
    #----------------------------
    # TEXT_NODES CRUD
    #----------------------------
    async def insert_text_node(self, text_range: Tuple[int, int], file_path: str, node_type: str) -> ObjectId:
        """Insert a new text_node document."""
        doc = {
            "text_range": text_range,
            "file_path": file_path,
            "node_type": node_type
        }
        result = await self.text_nodes.insert_one(doc)
        return result.inserted_id

    async def get_text_node(self, node_id: ObjectId) -> Union[TextNodeSchema, str]:
        """Fetch a text_node document by ID."""
        result = await self.text_nodes.find_one({"_id": node_id})
        if result:
            return result
        return "Text node not found"

    #----------------------------
    # SYMBOLS CRUD
    #----------------------------
    async def upsert_symbol(self, name: str, col: str, node_id: ObjectId) -> Optional[ObjectId]:
        """Add a node_id to the given symbol's column (defs, calls, asserts, types)."""
        update = {"$addToSet": {col: node_id}}
        result = await self.symbols.update_one({"name": name}, update, upsert=True)
        return result.upserted_id if result.upserted_id else None

    async def get_symbol(self, name: str) -> Union[SymbolSchema, str]:
        """Fetch a symbol document by name."""
        result = await self.symbols.find_one({"name": name})
        if result:
            return result
        return "Symbol not found"

    async def get_all_symbols(self) -> List[SymbolSchema]:
        """Return all documents from the symbols collection."""
        results = []
        async for doc in self.symbols.find({}):
            results.append(doc)
        return results
    
    #----------------------------
    # CHUNKS CRUD
    #----------------------------

    # Function to insert a single chunk into the MongoDB collection with validation.
    async def insert_chunk(self,chunk_data: dict) -> ObjectId | None:
        """
        Insert a single chunk.
        Returns inserted ID.
        """
        try:
            chunk = ChunkCreateSchema(**chunk_data)
        except ValidationError as e:
            print("Validation error while inserting chunk:", e)
            return None

        if await self.chunks_collection.find_one({"chunkId": chunk.chunkId}):
            print(f"Chunk with chunkId '{chunk.chunkId}' already exists.")
            return None
        result = await self.chunks_collection.insert_one(chunk.model_dump())
        return chunk.chunkId

    # Function to insert many chunks into the MongoDB collection with validation.
    async def insert_chunks(self, chunks_data: List[dict]) -> List[str]:
        """
        Insert multiple chunks with duplicate checking.
        Returns a list of inserted chunkIds.
        """
        valid_chunks = []

        # Validate and check duplicates
        for chunk_data in chunks_data:
            try:
                chunk = ChunkCreateSchema(**chunk_data)
                if not await self.chunks_collection.find_one({"chunkId": chunk.chunkId}):
                    valid_chunks.append(chunk.model_dump())
                else:
                    print(f"Skipping duplicate chunkId: {chunk.chunkId}")
            except ValidationError as e:
                print("Validation error:", e)

        if not valid_chunks:
            return []

        # Insert many
        try:
            result = await self.chunks_collection.insert_many(valid_chunks, ordered=False)
            inserted_ids = result.inserted_ids
        except BulkWriteError as e:
            print("Some duplicates were skipped.", e.details)
            inserted_ids = e.details.get("writeErrors", [])
            # Extract inserted ids if available
            inserted_ids = [item["op"]["chunkId"] for item in inserted_ids if "op" in item and "chunkId" in item["op"]]

        # Return list of inserted chunkIds
        return [chunk["chunkId"] for chunk in valid_chunks]

    # Function to retrieve  chunks by ChunkId from the MongoDB collection.
    async def get_chunk_by_id(self, chunk_id: str) -> Union[dict, None]:
        """ 
        Retrieve a chunk by its ID.
        """
        return await self.chunks_collection.find_one({"chunkId": chunk_id}, {"_id": 0})

    # Function to retrieve all chunks from the MongoDB collection.
    async def get_all_chunks(self, filter_query: dict = None, limit: int = 10) -> List[dict]:
        """
        Retrieve multiple chunks matching the filter.
        Returns a list of dictionaries.
        """
        filter_query = filter_query or {}
        cursor = self.chunks_collection.find(filter_query, {"_id": 0}).limit(limit)
        return [doc async for doc in cursor]

    # Function to update embedding status of a chunk by chunkId.
    async def update_embedding_status(self, chunk_id: str, status: bool) -> int:
        """
        Update the embedding status of a chunk.
        """
        result = await self.chunks_collection.update_one(
            {"chunkId": chunk_id},
            {"$set": {"isEmbedded": status}}
        )
        return result.modified_count

    # Function to update any fields of a single chunk by chunkID.
    async def update_chunk(self, chunk_id: str, updates: dict) -> int:
        """
        Update any fields of a single chunk by chunkId.
        Returns the number of documents modified (0 or 1).
        """
        try:
            valid_chunk = ChunkUpdateSchema(**updates)
            updates = valid_chunk.model_dump(exclude_unset=True)
        except ValidationError as e:
            print("Validation error while updating chunk:", e)
            return -1

        result = await self.chunks_collection.update_one(
            {"chunkId": chunk_id},
            {"$set": updates}
        )
        return result.modified_count
    
    # Function to update multiple chunks matching a filter query.
    async def update_chunks(self, filter_query: dict, updates: dict) -> int:
        """
        Update any fields for multiple chunks matching the filter.
        Returns the number of documents modified.
        """

        try:
            valid_chunk = ChunkUpdateSchema(**updates)
            updates = valid_chunk.model_dump(exclude_unset=True)
        except ValidationError as e:
            print("Validation error while updating chunks:", e)
            return -1

        result = await self.chunks_collection.update_many(
            filter_query,
            {"$set": updates}
        )
        return result.modified_count

    # Function to delete a chunk by chunkId.
    async def delete_chunk(self, chunk_id: str) -> int:
        """ 
        Delete a chunk by its ID.
        """
        result = await self.chunks_collection.delete_one({"chunkId": chunk_id})
        return result.deleted_count







