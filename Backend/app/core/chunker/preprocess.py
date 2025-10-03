import re
from typing import Any, Dict, List
from . import metta_ast_parser 
from app.db.db import Database 

# take the src code return the potential chunks retrieved from the symbol index table
async def preprocess_code(source_code: str, filepath: str, db: Database) -> List[List[int]]:
    tree = metta_ast_parser.parse(source_code)

    for idx,node in enumerate(tree):
        head_symbol = extract_symbol_from_node(node, source_code)

        if head_symbol["type"] == "unknown":
            continue

        if head_symbol["type"] == "comment":
            head_symbol["symbol"] = f"comment_{idx}"
            head_symbol["type"] = "def"

        if head_symbol["symbol"] == None:
            continue
        
        # insert text_node
        st, end = node.src_range
        node_id = await db.insert_text_node([st, end], filepath, node.node_type_str)

        # insert symbol
        await db.upsert_symbol(head_symbol["symbol"], head_symbol["type"] + "s", node_id)

    # fetch all symbols
    rows = await db.get_all_symbols()

    potential_chunks: List[List[int]] = []

    for row in rows:
        single_chunk: List[int] = []
        values = list(row.values())  # expected: [symbol, type, [ids...]]
        for ids in values[2:]:
            single_chunk.extend(ids)
        potential_chunks.append(single_chunk)

    # return the potential chunks
    return potential_chunks


def extract_symbol_from_node(node: metta_ast_parser.SyntaxNode, source_text: str) -> Dict[str, Any]:
    st, end = node.src_range
    code_snippet = source_text[st:end]

    if node.node_type_str == "RuleGroup":
        m = re.match(r'^\(\=\s*\(\s*([a-zA-Z0-9_-]+)', code_snippet)
        if m:
            return {"type": "def", "symbol": m.group(1)}

    elif node.node_type_str in ("CallGroup", "ExpressionGroup"):
        m = re.match(r'^\!\(\s*([a-zA-Z0-9_-]+)', code_snippet)
        if m:
            head = m.group(1)
            if head == "assertEqual":
                m2 = re.match(r'^\!\(assertEqual\s*\(\s*([a-zA-Z0-9_-]+)', code_snippet)
                if m2:
                    return {"type": "assert", "symbol": m2.group(1)}
                else:
                    return {"type": "assert", "symbol": None}
            else:
                return {"type": "call", "symbol": head}

    elif node.node_type_str == "TypeCheckGroup":
        m = re.match(r'^\(:\s*([a-zA-Z0-9_-]+)', code_snippet)
        if m:
            return {"type": "type", "symbol": m.group(1)}
    
    elif node.node_type_str == "Comment":
        return {"type": "comment", "symbol": None}

    return {"type": "unknown", "symbol": None}