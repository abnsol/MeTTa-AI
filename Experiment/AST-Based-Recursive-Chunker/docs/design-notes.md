# Notes on Building the MeTTa AST Chunker

This is a working doc for how I approached chunking in MeTTa using an AST parser, a Mongo db backend, and a symbol-aware preprocessing layer. It explains the why behind each decision.

---

## Starting Problem

Originally, I was already parsing MeTTa into an AST and chunking along AST node boundaries. That was better than fixed-line splits, but two problems remained:

1. Internal (inside a node)
   - Large AST nodes (e.g., big function/rule groups) could exceed the max chunk size.
   - Naively slicing those nodes fragmented semantics.

2. External (across nodes)
   - Related components (defs, types, asserts, calls) for the same symbol often lived in different AST nodes and got split apart.
   - The embedder wouldn’t “see” the full picture of a symbol in one chunk.

To address this, I added a middle layer between AST and chunking: a symbol-aggregation step that groups all code components that should be chunked together.

---

## Design Direction

Goal: produce chunks that follow semantic structure.

- Group by symbol: defs, types, asserts, and calls for the same head symbol should co-occur.
- Use AST for structure, but rely on a middle layer to aggregate semantics before chunking.

This is now AST-driven + symbol-aware chunking.

---

## Parser Upgrade

In metta_ast_parser, I diversified expression groups:

```python
# metta_ast_parser.py

class SyntaxNodeType(Enum):
    # ...
    ExpressionGroup = auto()
    CallGroup = auto()
    RuleGroup = auto()
    TypeCheckGroup = auto()
```

Recognizing RuleGroup separately lets us capture functions as proper units, rather than arbitrary expressions.

---

## Preprocessing Step (Middle Layer)

After parsing, I extract the head symbol(function name) for each relevant node and build a symbol index:

- defs → function/rule definitions
- types → type declarations
- asserts → assertEquals
- calls → executions

This index acts as a semantic aggregator so that chunking can group all expressions for a symbol together, regardless of where they appear in the file/module/repos.

---


## Database Collections (MongoDB)

There are 3 main collections in our MongoDB database (using PyMongo):

### 1. text_nodes

Stores code range (not the actual code) from AST nodes.

```json
{
  "_id": ObjectId,
  "text_range": [start, end],
  "file_path": "path/to/file.metta",
  "node_type": "RuleGroup"
}
```

- text_range: character offsets to slice original source (avoid duplication)
- file_path: path to the source file (currently a dummy path)
- node_type: rule, CallGroup, TypeCheckGroup, asserts, Comment, etc.

### 2. symbols

A lightweight index for semantic grouping.

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

- name: the symbol (function/variable)
- fields: lists of text_node ids for that symbol

### 3. chunks

Stores final chunked text based on the symbol index collection.

```json
{
  "_id": ObjectId,
  "chunk_text": "MeTTa code chunk..."
}
```

- Stores the actual chunk text (simple retrieval and embedding later)

---


## Why MongoDB?

- Schema-less, flexible document storage (no migrations needed)
- Fast, scalable, and easy to use with Python ([PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver))
- Arrays and references are natively supported in documents

---

## Chunker Changes

- Step 1: Parse → AST.
- Step 2: Build symbol index (middle layer) and persist text_nodes + symbols.
- Step 3: Group related nodes by symbol into potential chunks.
- Step 4: ChunkPreprocessedCode merges groups under max size.
  - If a node is too large → recursively split (ChunkCodeRecursively).
- Step 5: Store final chunks in Mongodb.

This avoids oversized nodes breaking the chunker while preserving semantics.

---


## Example Chunking Run

```bash
# Single-file run (legacy) // try on previous branches
python chunker.py input.metta output.txt --max-size 500

# Repo-level chunking (new)
python chunker.py --max-size 500
```

Output:

- Chunked code stored in DB.
- Related defs/types/asserts/calls grouped by symbol.
- Oversized nodes recursively split.
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

## Next Steps

- Further improvements to cross-file symbol aggregation and repo-level analytics.
- Persist real file_path values per node (currently using a demo file path).
- Chunking Comments with functions by proximity.