# Import relevant libraries
import json
from pathlib import Path
import pandas as pd
import os
import sys
from pathlib import Path

# Import custom functions from other folders
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  
from utils.data_utils import check_paths_exists, get_file_name_from_index_element


def get_index_metadata(master_file_path: str) -> list[dict]:
    """
    Read Excel file and return index metadata as a list of dictionaries.
 
    :param master_file_path: The path to the Excel file containing the index metadata.  
    :return: A list of dictionaries representing the rows in the Excel file.  
    """
    df = pd.read_excel(master_file_path)
    df = df.fillna("")
    return df.to_dict(orient="records")


def build_index_structure(index_metadata: list[dict], base_path: str):
    """
    Build index structure based on metadata.
    
    :param index_metadata: A list of dictionaries containing index metadata.  
    :param base_path: The base path where the index structure will be built.  
    """
    for index_element in index_metadata:
        index_element["content"] = ""
        json_name = get_file_name_from_index_element(index_element) + ".json"
        index_folder_path = Path(base_path) / json_name

        if not index_folder_path.exists():
            with open(index_folder_path, "w") as file:
                json.dump(index_element, file)


def create_index_without_content(
    input_documents_folder: str, local_index_folder: str, master_file_path: str
):
    """
    Set up the index structure from the input documents and master metadata file. This function checks the existence of the specified paths, reads the index metadata  
    from the master file, and builds the index structure in the local index folder.  
  
    :param input_documents_folder: The path to the folder containing input documents.  
    :param local_index_folder: The path to the folder where the index structure will be stored.  
    :param master_file_path: The path to the Excel file containing the index metadata.  
    """
    check_paths_exists([local_index_folder, input_documents_folder, master_file_path])
    index_metadata = get_index_metadata(master_file_path)
    build_index_structure(index_metadata, local_index_folder)
