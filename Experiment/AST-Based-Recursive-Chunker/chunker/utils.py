import os 
import hashlib


def _build_chunk_doc(chunk_text: str, rel_path: str) -> dict:
    """Build a Chunk Create-style document for insertion."""

    # Derive identifiers
    parts = rel_path.split("/", 1)
    repo_name = parts[0] if parts else "unknown-repo"
    inside_repo = parts[1] if len(parts) > 1 else ""
    section = os.path.dirname(inside_repo).replace("\\", "/") if inside_repo else None
    file_name = os.path.basename(inside_repo) if inside_repo else rel_path

    # chunk id using content + rel_path
    chunk_id = hashlib.sha256(f"{rel_path}:{chunk_text}".encode("utf-8")).hexdigest()[:16]

    return {
        "chunkId": chunk_id,
        "source": "code",
        "chunk": chunk_text,
        "project": repo_name,   # same as repo for now
        "repo": repo_name,
        "section": section if section else None,
        "file": file_name,
        "version": "1",      # or a commit hash if available
        "isEmbedded": False,
        "description": None     # fill later
    }