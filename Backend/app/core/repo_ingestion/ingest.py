import shutil
from clone import clone_repo, get_all_files
from filters import process_metta_files
from config import TEMP_DIR, DATA_DIR
from loguru import logger

def ingest_pipeline(repo_url: str) -> None:
    repo_path: str = clone_repo(repo_url, TEMP_DIR)
    
    try:
        files: list[str] = get_all_files(repo_path)
        process_metta_files(files, DATA_DIR, repo_root=repo_path)
    finally:
        logger.info(f"Cleaning up {repo_path}")
        shutil.rmtree(repo_path, ignore_errors=True)
