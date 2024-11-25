# Import relevant libraries
import tempfile
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

INDEX_MASTER_FILE_NAME = os.getenv("INDEX_MASTER_FILE_NAME")
FOLDER_PATH = os.getenv("FOLDER_PATH")


def _temporary_directory() -> str:
    """
    Return a temporary directory path.
    
    :return: string representing the temporary directory path
    """
    return FOLDER_PATH
    with tempfile.TemporaryDirectory() as temp_dir:
        return temp_dir


def setup_local_folders() -> tuple[str]:
    """
    Create and return the local folders created in the temporary directory. 
    4 folders are created, one for each step of the indexation. 

    :return: tuple containing the path to each folder as strings.
    """
    temporary_directory_path = Path(_temporary_directory())
    
    # Defining the folder names
    input_documents_folder = temporary_directory_path / "input_documents"
    local_index_without_content_folder = (
        temporary_directory_path / "index_without_content"
    )
    local_index_with_chunked_content_folder = (
        temporary_directory_path / "index_with_chunked_content"
    )
    local_index_embedded_folder = temporary_directory_path / "index_embedded"

    master_file_path = input_documents_folder / INDEX_MASTER_FILE_NAME

    # Creating folder in temporary directory
    for folder in [
        input_documents_folder,
        local_index_without_content_folder,
        local_index_with_chunked_content_folder,
        local_index_embedded_folder,
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    return (
        input_documents_folder,
        local_index_without_content_folder,
        local_index_with_chunked_content_folder,
        local_index_embedded_folder,
        master_file_path,    )
