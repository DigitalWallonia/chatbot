# Import relevant libraries
import os
import logging
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from pathlib import Path
import shutil

load_dotenv(override=True)

AZURE_BLOB_ENDPOINT = os.getenv("AZURE_BLOB_ENDPOINT")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME")

def get_blob_sas_token() -> str:
    """
    Retrieve SAS token from environment variables. This function fetches the SAS token required for accessing Azure Blob Storage  
    from the environment variables.  
  
    :return: The SAS token.
    """
    # TODO: dynamically generate SAS token
    token = os.getenv("AZURE_BLOB_SAS_TOKEN")
    logging.info(AZURE_BLOB_ENDPOINT)
    logging.info(token)
    return token


def get_blob_service_client(sas_token: str) -> BlobServiceClient:
    """
    Create and return BlobServiceClient instance using the provided SAS token.  
  
    :param sas_token: The SAS token for accessing Azure Blob Storage.  
    :return: An instance of BlobServiceClient.
    """
    return BlobServiceClient(AZURE_BLOB_ENDPOINT, credential=sas_token)


def download_blob(blob_client, local_path: str):
    """
    Download a blob to the specified local path.

    :param blob_client: The blob client to download from.  
    :param local_path: The local file path where the blob content will be saved.  
    :return: This function does not return any value.
    """
    with open(local_path, "wb") as file:
        logging.info(f"AZURE_STORAGE_HELPER: downloading blob to {local_path}")
        file.write(blob_client.download_blob().readall())


def _download_blob_container_to_local_folder(
    blob_url: str, local_folder_path: str, credentials: str
):
    """
    Download all blobs from the container to the local folder.
    
    :param blob_url: The URL of the blob container.  
    :param local_folder_path: The local folder path where the blobs will be saved.  
    :param credentials: The SAS token or other credentials for accessing the blob container.  
    :return: This function does not return any value.
    """
    local_folder_path = Path(local_folder_path)
    blob_service_client = get_blob_service_client(credentials)
    container_client = blob_service_client.get_container_client(
        AZURE_BLOB_CONTAINER_NAME
    )

    for blob_name in container_client.list_blob_names():
        blob_client = container_client.get_blob_client(blob_name)
        local_path = local_folder_path / blob_name

        if not local_path.exists():
            download_blob(blob_client, local_path)


def download_blob_container_to_local_folder(
    blob_url: str, local_folder_path: str, credentials: str
):
    """
    Validates the input parameters and delegates the task of downloading  
    all blobs in the container to the local folder.  
    
    :param blob_url: The URL of the blob container.  
    :param local_folder_path: The local folder path where the blobs will be saved.  
    :param credentials: The SAS token or other credentials for accessing the blob container.  
  
    """
    # TODO: check blob url
    # TODO: check local folder path
    # TODO: check credentials

    _download_blob_container_to_local_folder(blob_url, local_folder_path, credentials)


# def download_documents_from_blob_to_path(local_folder_path: str, azure_blob_endpoint:str = AZURE_BLOB_ENDPOINT):
#     sas_token = get_blob_sas_token()
#     download_blob_container_to_local_folder(
#         azure_blob_endpoint, local_folder_path, sas_token
#     )

def download_documents_from_blob_to_path(local_folder_path: str, input_document_folder: str):
    """
    Iterates over all files in the local folder and copies them to  
    the input document folder.  
  
    :param local_folder_path: The local folder path where the documents are initially stored.  
    :param input_document_folder: The destination folder where the documents will be copied.  
  
    """
    logging.info(input_document_folder)
    for name in os.listdir(local_folder_path):
        # Open file
            with open(os.path.join(local_folder_path, name)) as f:
                print(f"Content of '{name}'")
                # Read content of file
                shutil.copy2(os.path.join(local_folder_path, name), os.path.join(input_document_folder, name))