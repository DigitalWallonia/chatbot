# Import relevant libraries
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Import custom functions from other folders
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  
from utils.data_utils import (
    check_paths_exists,
    get_file_name_from_index_element,
    read_index_element_from_path,
    push_entry_to_path,
)
from utils.RDF import ScrapingRDF

load_dotenv(override=True)

INDEX_TTL_FILENAME_COLUMN = os.getenv("INDEX_TTL_FILENAME_COLUMN")
INDEX_TAXO_NAME_COLUMN = os.getenv("INDEX_TAXO_NAME_COLUMN")

def _create_index_of_entry_with_chunked_content(
    ttl_path: Path, ttl: str, entry_with_chunked_content_path: Path
):
    """
    Processes RDF data from a given ttl (Turtle) file and pushes the  
    processed entry to a specified path
    
    :param ttl_path: The path to the ttl file containing RDF data.  
    :param ttl: The name of the ttl file in string format.  
    :param entry_with_chunked_content_path: The path where the processed entry with chunked content will be stored.  
    """

    index_entries = ScrapingRDF().ScrapeRDF({ttl_path: ttl}, [])
    push_entry_to_path(index_entries, entry_with_chunked_content_path)


def _create_index_with_chunked_content(
    input_documents_folder: Path,
    local_index_without_content_folder: Path,
    local_index_with_chunked_content_folder: Path,
):
    """
    Processes RDF data from input documents and updates index elements,  
    which initially lack content, by adding chunked content to them. The updated index  
    elements are then saved to a specified folder.

    :param input_documents_folder: The folder containing the input documents in ttl format.  
    :param local_index_without_content_folder: The folder containing index elements without content.  
    :param local_index_with_chunked_content_folder: The folder where the updated index elements with chunked content will be stored.  
    """
    # Get all index elements without content
    entries_without_content_paths = local_index_without_content_folder.glob("*.json")

    # Iterate over all index elements without content
    for entry_without_content_path in entries_without_content_paths:
        # Read index element
        entry = read_index_element_from_path(entry_without_content_path)
        entry_id = get_file_name_from_index_element(entry)
        entry_with_chunked_content_path = local_index_with_chunked_content_folder / str(
            entry_id + ".json"
        )

        ttl_path = input_documents_folder / entry[INDEX_TTL_FILENAME_COLUMN]

        ttl = entry[INDEX_TAXO_NAME_COLUMN] #get_clean_pdf_document(ttl_path, entry)
        _create_index_of_entry_with_chunked_content(
            entry, ttl_path, ttl, entry_with_chunked_content_path
        )


def create_index_with_chunked_content(
    input_documents_folder: str,
    local_index_without_content_folder: str,
    local_index_with_content_folder: str,
):
    """
    Validates the existence of the provided folder paths, converts them  
    to `Path` objects, and then delegates the task of creating an index with chunked  
    content to an internal helper function.

    :param input_documents_folder: The path to the folder containing input documents in ttl format.  
    :param local_index_without_content_folder: The path to the folder containing index elements without content.  
    :param local_index_with_content_folder: The path to the folder where the updated index elements with chunked content will be stored.  
    """
    check_paths_exists(
        [
            input_documents_folder,
            local_index_without_content_folder,
            local_index_with_content_folder,
        ]
    )

    # Convert to Path objects
    input_documents_folder = Path(input_documents_folder)
    local_index_without_content_folder = Path(local_index_without_content_folder)
    local_index_with_content_folder = Path(local_index_with_content_folder)

    _create_index_with_chunked_content(
        input_documents_folder,
        local_index_without_content_folder,
        local_index_with_content_folder,
    )
