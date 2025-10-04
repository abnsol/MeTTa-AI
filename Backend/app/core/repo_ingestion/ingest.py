import os,sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  

import shutil
from clone import clone_repo, get_all_files
from filters import process_metta_files
from config import TEMP_DIR, DATA_DIR
from loguru import logger
from chunker.chunker import ast_based_chunker
import asyncio

def ingest_pipeline(repo_url: str) -> None:
    repo_path: str = clone_repo(repo_url, TEMP_DIR)
    
    try:
        files: list[str] = get_all_files(repo_path)
        indexes = process_metta_files(files, DATA_DIR, repo_root=repo_path)
        asyncio.run(ast_based_chunker(indexes))
    finally:
        logger.info(f"Cleaning up {repo_path}")
        shutil.rmtree(repo_path, ignore_errors=True)

# TEST
if __name__ == "__main__":
    # test_repo: str = "https://github.com/iCog-Labs-Dev/metta-moses.git"
    test_repo: str = "https://github.com/iCog-Labs-Dev/hyperon-openpsi.git"

    ingest_pipeline(test_repo)