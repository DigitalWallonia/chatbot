# Import relevant libraries
import os
import json
import pathlib
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SimpleField,
    SearchFieldDataType,
    SemanticField,
    VectorSearchProfile,
    SemanticSettings,
    VectorSearchAlgorithmKind,
    HnswVectorSearchAlgorithmConfiguration,
    SemanticConfiguration,
    SearchIndex,
    PrioritizedFields,
    VectorSearch,
    AzureOpenAIVectorizer,
    AzureOpenAIParameters,
    HnswParameters,
)


load_dotenv(override=True)

AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)

AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_API_VERSION"
)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")


def CreateOrUpdateIndexOnAzure():
    """
    Create or update a search index on Azure Search service. This function configures and creates (or updates) a search index on Azure Search service,  
    including fields, vector search configurations, and semantic configurations.  
    """
    IndexClient = SearchIndexClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT, credential=credential
    )

    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            retrievable = True,
        ),
        SearchableField(name="uri", type=SearchFieldDataType.String, filterable = True),
        SearchableField(name="Taxonomie", type=SearchFieldDataType.String, filterable = True),
        SearchableField(name="Libelle_Definition", type=SearchFieldDataType.String, filterable = True),
        SearchableField(name="Parents", type=SearchFieldDataType.String, retrievable = True),
        SearchableField(name="triples", type=SearchFieldDataType.String, retrievable = True),
        SearchField(
            name="Libelle_Definition_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile="myHnswProfile",
        ),
    ]

    # Configure the vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswVectorSearchAlgorithmConfiguration(
                name="myHnsw",
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters=HnswParameters(
                    m=4, ef_construction=400, ef_search=500, metric="cosine"
                ),
            ),
        ],
        profiles=[
            VectorSearchProfile(name="myHnswProfile", algorithm="myHnsw", vectorizer="myVectorizer"),
        ],
        vectorizers=[
        AzureOpenAIVectorizer(
            name="myVectorizer",
            azure_open_ai_parameters=AzureOpenAIParameters(
                resource_uri=AZURE_OPENAI_ENDPOINT,
                deployment_id = AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                model_name=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                api_key=AZURE_OPENAI_API_KEY
            )
        )
    ]
    )

    semantic_config = SemanticConfiguration(
        name="openai-poc-semantic-config",
        prioritized_fields=PrioritizedFields(
            title_field=SemanticField(field_name="Libelle_Definition"),
            prioritized_content_fields=[SemanticField(field_name="Libelle_Definition"), SemanticField(field_name="Parents")],
        ),
    )

    # # Create the semantic settings with the configuration
    semantic_settings = SemanticSettings(configurations=[semantic_config])

    # Create the search index with the semantic settings
    index = SearchIndex(
        name=AZURE_SEARCH_INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_settings=semantic_settings,
    )
    result = IndexClient.create_or_update_index(index)
    logging.info(f" {result.name} created")


def GetSearchClient():
    """
    Create and return a SearchClient instance. This function initializes and returns a SearchClient instance for interacting  
    with the Azure Search service.  

    :return: An instance of SearchClient. 
    """
    return SearchClient(
        endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=credential,
    )


def UploadIndexToAzure(FolderPath: str):
    """
    Upload index documents from the specified folder to Azure Search service. This function reads JSON files from the specified folder and uploads the index  
    documents to Azure Search service.  
  
    :param FolderPath: The path to the folder containing index documents in JSON format.  
    """
    index_client = GetSearchClient()
    index_entry_paths = pathlib.Path(FolderPath).glob("*")
    failed_to_upload = []
    for entry_path in index_entry_paths:
        try:
            with open(entry_path) as file:
                index_list = json.load(file)
                for index in index_list:
                    # if not is_document_in_azure(index["id"]):
                    logging.info(f"Uploading {index['id']}")
                    index_client.upload_documents(documents=[index])
        except Exception as e:
            logging.info(entry_path)
            logging.info(e)
            # raise e
            failed_to_upload.append(entry_path)

    logging.info(failed_to_upload)
