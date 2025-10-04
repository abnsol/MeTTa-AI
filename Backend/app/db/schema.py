from pydantic import BaseModel, Field
from typing import Optional, Literal

# Set up MongoDB schema/collections for creating chunks and metadata.
class ChunkCreateSchema(BaseModel):
    chunkId: str = Field(..., min_length=1)
    source: Literal["code", "specification", "documentation"]
    chunk: str = Field(..., min_length=1)
    project: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    file: list[str] = Field(..., min_length=1)
    isEmbedded: bool = False

    # Often omitted at create-time
    section: Optional[list[str]] = None
    version: Optional[str] = None
    description: Optional[str] = None    

# Schema for updating chunk metadata; all fields optional.
class ChunkUpdateSchema(BaseModel):
    chunkId: str
    source: Optional[Literal["code", "specification", "documentation"]]
    chunk: Optional[str]
    project: Optional[str]
    repo: Optional[str]
    section: Optional[list[str]]
    file: Optional[list[str]]
    version: Optional[str]
    isEmbedded: Optional[bool]
    description: Optional[str]

