import asyncio
import os
import argparse
import metta_ast_parser 
from typing import List
from db import Database as DB
from dotenv import load_dotenv
from preprocess import preprocess_code
import json
from collections import defaultdict

# Recursive Chunking Algorithm (with source_code passed as an argument)

def getSize(node: metta_ast_parser.SyntaxNode) -> int:
    """Gets the size of a node based on its source text length."""
    start, end = node.src_range
    return end - start

async def ChunkPreprocessedCode(potential_chunks, max_size: int, db: DB, source_code: str) -> List[str]:
    """Chunks a list of potential chunks based on max_size.
    Each potential chunk is a list of text_node table IDs from our db.
    Returns a list of chunked code strings.
    """
    chunks = []

    for chunk_ids in potential_chunks:
        chunk, chunk_size = [], 0
        for chunk_id in chunk_ids:
            text_range = await db.get_text_node(chunk_id)
            text_range = text_range["text_range"]
            text_node = source_code[text_range[0]:text_range[1]]
            text_size = len(text_node)
            
            # when single text node is larger than max_size
            if text_size > max_size:
                if chunk:
                    chunks.append("\n".join(chunk))
                    chunk, chunk_size = [], 0
                # recursively split this big single node
                nodes = metta_ast_parser.parse(text_node)[0]
                subChunks = ChunkCodeRecursively(nodes, text_node, max_size)
                chunks.extend(subChunks)

            # when adding this text node exceeds max_size
            elif chunk_size + text_size > max_size:
                if chunk:
                    chunks.append("\n".join(chunk))
                chunk, chunk_size = [], 0
            else:
                chunk.append(text_node)
                chunk_size += text_size

        if chunk:
            chunks.append("\n".join(chunk))

    return chunks

async def ChunkCode(code: str, max_size: int, db, rel_path: str) -> List[str]:
    """
    Chunks the code into smaller pieces based on the max_size.
    Stores the chunks in the database.
    """


    
    # for now lets pass the code to the chunker
    # later we can add a feature to fetch the source code from the db using the file_path
    potential_chunks = await preprocess_code(code, rel_path, db)
    chunks = await ChunkPreprocessedCode(potential_chunks, max_size, db, code)
    ids = await db.insert_chunks(chunks)
    return chunks

def ChunkCodeRecursively(node: metta_ast_parser.SyntaxNode ,text: str, max_size: int) -> list[str]:
    """Recursively chunks a potential chunk (syntax node) when it exceeds max_size."""
    if getSize(node) <= max_size:
        st, en = node.src_range
        return [text[st:en]]

    # No children to recurse into, accept oversized node
    if not node.sub_nodes:  
        st, en = node.src_range
        return [text[st:en]]

    chunks = []
    for sub_node in node.sub_nodes:
        sub_chunks = ChunkCodeRecursively(sub_node, text, max_size)
        if chunks and len(chunks[-1]) + len(sub_chunks[0]) <= max_size:
                chunks[-1] += "\n" + sub_chunks[0]
                sub_chunks = sub_chunks[1:]

        chunks.extend(sub_chunks)
    return chunks


async def main(max_size=500):    
    load_dotenv() 

    db = DB(os.getenv("mongo_uri"), "MeTTa_Chunker")
    await db.clear_all_collections() # "JUST FOR DEVELOPMENT"

    # Load the index file mapping hashes to relative paths
    with open("example_metta_index.json") as f:
        index = json.load(f)

    # Group files by repo (can adjust this by determining scope)
    repo_files = defaultdict(list)
    for file_hash, rel_path in index.items():
        repo_name = rel_path.split('/')[0]
        repo_files[repo_name].append((file_hash, rel_path))
    
    for repo_name, files in repo_files.items():
        print(f"Processing repo: {repo_name}")
        for file_hash, rel_path in files:
            file_path = rel_path  # or your actual path
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                await ChunkCode(code, max_size,db, rel_path)
                print(f"Processed file: {file_path}")
            except FileNotFoundError:   
                print(f"Error: Input file not found at '{file_path}'")
                continue
            except Exception as e:
                print(f"Error processing file '{file_path}': {e}")
                continue
        # After all files in this repo are processed, reset symbols
        # await db.clear_text_nodes_symbols() 

    print("Chunks Stored in database")
    print("Chunking complete!")

if __name__ == "__main__":
    asyncio.run(main())
