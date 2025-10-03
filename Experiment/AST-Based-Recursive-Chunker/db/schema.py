from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId

# Set up MongoDB schema/collections for creating chunks and metadata.
class ChunkCreateSchema(BaseModel):
    chunkId: str = Field(..., min_length=1)
    source: Literal["code", "specification", "documentation"]
    chunk: str = Field(..., min_length=1)
    project: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    file: str = Field(..., min_length=1)

    # Often omitted at create-time
    section: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None

    # Defaults mean you can omit this at create-time
    isEmbedded: bool = False

# Schema for updating chunk metadata; all fields optional.
class ChunkUpdateSchema(BaseModel):
    chunkId: str
    source: Optional[Literal["code", "specification", "documentation"]]
    chunk: Optional[str]
    project: Optional[str]
    repo: Optional[str]
    section: Optional[str]      
    file: Optional[str]
    version: Optional[str]
    isEmbedded: Optional[bool]
    description: Optional[str]

class TextNodeSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    text_range: Tuple[int, int]
    file_path: str
    node_type: str


class SymbolSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True) 
    name: str
    defs: List[ObjectId] = Field(default_factory=list)
    calls: List[ObjectId] = Field(default_factory=list)
    asserts: List[ObjectId] = Field(default_factory=list)
    types: List[ObjectId] = Field(default_factory=list)


class ChunkSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    chunk_text: str