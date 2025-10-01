# Chunking

The goal of selecting the best chunking strategy is to make each chunk as meaningful and complete as possible.  
Semantically similar code should stay together so that a chunk represents a full, coherent unit.  
This is our final goal.

Any vector store requires chunking large documents for effective search.

> Further reading: Design Notes [docs/design-notes.md](docs/design-notes.md)

---

## What’s new in this iteration

**Now:**  
We have migrated to **MongoDB** for greater flexibility, scalability, and speed.  

This makes it easier to evolve our data model as the project grows.

- **Collections:**  
  - `text_nodes`: Stores code ranges and metadata for each AST node.
  - `symbols`: Stores symbol information (definitions, calls, asserts, types) as arrays of references to `text_nodes`.
  - `chunks`: Stores the final code chunks for retrieval and embedding.

- **Why MongoDB?**
  - No schema migrations needed—collections and documents can evolve naturally.
  - Fast, scalable, and easy to use with Python via [PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver).
  - Flexible document structure: each collection contains all the information previously stored in SQL tables, but now as documents.

---

## Why not store whole files in vector databases?

- Context windows of models are limited.
- Smaller & concise chunks better match specific queries and avoid noise.
- Ideal strategy: use the smallest chunk that still contains all relevant context.

---

## Suitable Chunk Size for Open Source Model Context Windows

- Current open-source LLMs have context windows ~512–1500 tokens.
- Approximate ratio: 1 token ≈ 5 characters.
- To fit within windows, chunk size ≈ 1500–6500 characters (excluding prompt tokens).

---

## How can we chunk code files?

There are 4 main strategies:

1. Heuristic (fixed size)  
2. Rule-based (using delimiters)  
3. Overlapping (sliding window)  
4. Syntax-aware chunking (AST-based)

Problems with the first two:
- Heuristic & rule-based approaches ignore semantics and split code incorrectly.

Our approach: Syntax-aware + symbol-aware chunking
- Parse into an AST for structure.
- Middle layer aggregates related code by head symbol (defs, types, asserts, calls).
- Chunk the aggregated groups, recursively splitting only when size requires.

Steps:
1. Generate AST structure.
2. Build symbol index (defs/types/asserts/calls).
3. Chunk groups under a max size with recursive splitting for large nodes.

---

## Architecture Overview

1. Parse MeTTa file → AST.
2. Extract head symbols per relevant node.
3. Persist nodes into text_nodes (text_range + file_path + node_type).
4. Update symbols table with node IDs grouped by name (defs, calls, asserts, types).
5. Preprocess → build potential chunks by symbol association.
6. Chunking:
   - Merge related nodes into chunks up to max_size.
   - If a node is too large, split recursively by its sub-nodes.
7. Store final chunks (chunk_text) in Mongo db.

---

## Example Document Structures

**text_nodes**
```json
{
  "_id": ObjectId,
  "text_range": [start, end],
  "file_path": "path/to/file.metta",
  "node_type": "RuleGroup"
}
```

**symbols**
```json
{
  "_id": ObjectId,
  "name": "symbol_name",
  "defs": [text_node_id, ...],
  "calls": [text_node_id, ...],
  "asserts": [text_node_id, ...],
  "types": [text_node_id, ...]
}
```

**chunks**
```json
{
  "_id": ObjectId,
  "chunk_text": "MeTTa code chunk..."
}
```
---

## Getting the Best Out of Chunks

- Denoising: keep the smallest relevant chunk.
- Coalescing: remove whitespace.
- Handle deep/large code via recursive splitting and reconstruction.
- If a single syntax node exceeds context window → split recursively.
- Dynamic chunk sizing: tune for model limits.
- Optional overlap to improve retrieval coverage.
- Enhanced embeddings: add natural language descriptions.

Note: When embedding, store both vectors + raw chunks.

---

## Strategies for Large Code Repositories

- Repo-level filtering: focus on “golden repos”.
- Selective parsing: only MeTTa files.
- Different splitters: docs vs code.
- Next: traverse repos and persist true file_path (we currently use a demo path).

---

## Large Scale Data Ingestion Pipeline Plan

![Ingest pipeline](docs/ingest-pipeline.png)

---

## Problems and Ongoing Work

- MeTTa parser lacked richer node types; we extended groups:
  - ExpressionGroup, CallGroup, RuleGroup, TypeCheckGroup.
- Remaining work:
  - Repository-level traversal and cross-file symbol aggregation.
  - Indexing/constraints for faster lookups and integrity.
  - Optional source maps for traceability.

---

## Configuration

Create a .env:

```env
mongo_uri=mongodb://localhost:27017
```

---


## Running the Chunker

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Repo-level chunking (new)
python chunker.py --max-size 1500
```

Outputs:
- Chunked code stored in DB (chunks collection).
- Related defs/types/asserts/calls grouped by symbol.
- Oversized nodes recursively split while preserving semantics.
- For repo-level runs: all files in a repo are processed together, with correct symbol scoping per repo.

---

## Repo-Level Chunking

The chunker now supports processing an entire repository at once:

- Reads a JSON index (e.g., `metta_index.json`) mapping file hashes to their repo-relative paths.
- Groups files by repository, then iterates through each file in a repo.
- Chunks each file and stores the results in MongoDB.
- Ensures symbol scoping is correct by allowing symbol tables to be reset per repo.

This enables scalable, automated chunking for large codebases and supports downstream retrieval and embedding workflows.

---

## Resources

- Chunking 2M Files (Sweep Docs, archived)  
  https://web.archive.org/web/20240413093103/https://docs.sweep.dev/blogs/chunking-2m-files
- RAG For a Codebase with 10k Repos  
  https://www.qodo.ai/blog/rag-for-large-scale-code-repos/
- cAST: Enhancing Code Retrieval-Augmented Generation with Structural Chunking via Abstract Syntax Tree  
  https://arxiv.org/pdf/2506.15655
- DataCamp: PostgreSQL + Python Tutorial  
  https://www.datacamp.com/tutorial/tutorial-postgresql-python
- Building Python Apps with PostgreSQL and psycopg3 (TigerData)  
  https://www.tigerdata.com/learn/building-python-apps-with-postgresql
- Symbol Table in compilers
  https://www.geeksforgeeks.org/compiler-design/symbol-table-compiler
- PyMongo
  https://www.mongodb.com/docs/languages/python/pymongo-driver 