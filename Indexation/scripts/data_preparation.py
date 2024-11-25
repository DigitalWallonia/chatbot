# Import relevant libraries
import os
import logging
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

# Import custom functions from other folders
from index_with_chunked_content import create_index_with_chunked_content
from index_without_content import create_index_without_content
from index_embedder import create_embedded_index
from utils.AzureSearchHelper import (
    CreateOrUpdateIndexOnAzure,
    UploadIndexToAzure,
)
from utils.azure_storage_helper import download_documents_from_blob_to_path
from file_structure import setup_local_folders
from utils.AzureSearchHelper import (
    CreateOrUpdateIndexOnAzure,
    UploadIndexToAzure,
)

load_dotenv()

AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_ENDPOINT")

def create_index():
    """
    create_index creates and uploads documents from a blob storage (or local folder) to an Azure AI index based on the environment variables defined 
    """
    logging.info("DATA PREPARATION: setup_local_folders")
    (
        input_documents_folder,
        local_index_without_content_folder,
        local_index_with_chunked_content_folder,
        local_index_embedded_folder,
        master_file_path,
    ) = setup_local_folders()

    logging.info("DATA PREPARATION: download_documents_from_blob_to_path")
    download_documents_from_blob_to_path(AZURE_BLOB_CONTAINER_NAME, input_documents_folder)
    create_index_without_content(
        input_documents_folder, local_index_without_content_folder, master_file_path
    )
    create_index_with_chunked_content(
        input_documents_folder,
        local_index_without_content_folder,
        local_index_with_chunked_content_folder,
    )

    logging.info("DATA PREPARATION: create_embedded_index")
    create_embedded_index(
        local_index_with_chunked_content_folder, local_index_embedded_folder
    )

    logging.info("DATA PREPARATION: create_or_update_index_on_azure")
    CreateOrUpdateIndexOnAzure()
    logging.info("DATA PREPARATION: upload_index_to_azure")
    UploadIndexToAzure(local_index_embedded_folder)

if __name__=="__main__":

    create_index()
