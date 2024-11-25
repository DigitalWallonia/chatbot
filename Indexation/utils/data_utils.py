# Import relevant libraries
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

INDEX_TTL_FILENAME_COLUMN = os.getenv("INDEX_TTL_FILENAME_COLUMN")
INDEX_TAXO_COLUMN = os.getenv("INDEX_TAXO_COLUMN")


def push_entry_to_path(entry: dict, path: str):
    """
    Save a dictionary entry to a specified file path in JSON format. This function writes the provided dictionary entry to a file at the specified  
    path in JSON format.  
  
    :param entry: The dictionary entry to be saved.  
    :param path: The file path where the entry will be saved.
    """
    with open(path, "w") as file:
        json.dump(entry, file)


def read_index_element_from_path(path: str) -> dict:
    """
    Read index element from path. This function reads the content of a JSON file at the specified path and returns  
    it as a dictionary.  
  
    :param path: The file path from which to read the dictionary entry.  
    :return: The dictionary entry read from the file. 
    """
    with open(path) as file:
        return json.load(file)


def check_paths_exists(paths: list[str] ):
    """
    Check if the specified paths exist and raise an exception if any do not.  
  
    :param paths: The list of paths to be checked.  
    """
    for path in paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"ERROR: Path does not exist: {path}")


def get_file_name_from_index_element(index_element: dict) -> str:
    """
    Extracts and returns the file name (excluding extension) from the provided index element. This function attempts to extract the file name from the index element using  
    the column specified by the `INDEX_TTL_FILENAME_COLUMN` environment variable. If the extraction fails, it falls back to using the `INDEX_TAXO_COLUMN` environment variable.  
  
    :param index_element: The dictionary containing the index element data.  
    :return: The extracted file name (excluding extension).
    """
    try:
        return index_element[INDEX_TTL_FILENAME_COLUMN][:-4]
    except:
        return index_element[INDEX_TAXO_COLUMN]