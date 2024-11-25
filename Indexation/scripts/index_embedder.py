# Import relevant libraries
from pathlib import Path
import gc
import os
import logging
from dotenv import load_dotenv

# Import custom functions from other folders
from utils.data_utils import (
    check_paths_exists,
    get_file_name_from_index_element,
    read_index_element_from_path,
    push_entry_to_path,
)
from utils.AzureOpenaiHelper import text_to_embedding


load_dotenv(override=True)

INDEX_VECTOR_COLUMNS = os.getenv("INDEX_VECTOR_COLUMNS").split("|")

def embed_index_elements(index_elements: list[dict]) -> list[dict]:
    """
    Embed the content columns of each item (chunked documents) from an index (represented as a list of dictionaries)

    :param index_elements: list of dict where each dictionary is one document from the index
    :return: updated version of index_elements (extra column containing the vector embedding for each document) 
    """
    for index_element in index_elements:
        logging.info(index_element)
        column_vector = f"{INDEX_VECTOR_COLUMNS[0]}_vector"
        index_element[column_vector] = text_to_embedding(f"{index_element[INDEX_VECTOR_COLUMNS[0]]}. {index_element[INDEX_VECTOR_COLUMNS[1]]}")
        
    return index_elements


def create_embedded_index(
    local_index_with_chunked_content_folder: str, local_index_embedded_folder: str
):
    """
    Create a local index containing an extra field: vector embeddings

    :param local_index_with_chunked_content_folder: string of the folder where the index with chunked content is stored
    :param local_index_embedded_folder: string of the folder where the index with embedded content should be stored
    """
    check_paths_exists(
        [local_index_with_chunked_content_folder, local_index_embedded_folder]
    )

    # Get all chunked index elements
    entries_with_chunked_content_paths = Path(
        local_index_with_chunked_content_folder
    ).glob("*.json")

    # Iterate over all chunked index elements
    for entry_with_chunked_content_path in entries_with_chunked_content_paths:
        # Read index element
        entry = read_index_element_from_path(entry_with_chunked_content_path)
        entry_id = get_file_name_from_index_element(entry[0])

        entry_embedded_path = Path(local_index_embedded_folder) / str(
            entry_id + ".json"
        )

        if entry_embedded_path.exists() or not INDEX_VECTOR_COLUMNS:
            continue

        logging.info(
            f"INDEX_EMBEDDER: create_embedded_index: {entry_with_chunked_content_path}"
        )

        index_elements = embed_index_elements(entry)
        push_entry_to_path(index_elements, entry_embedded_path)

        # Trying to free up memory
        del entry
        del entry_id
        del entry_embedded_path
        del index_elements

        gc.collect()
