# Taxonomy indexation app

## Overview

The taxonomy indexation app is a Python application designed to read and process TTL files from an Azure Blob container or a local folder, and a master information file in XLSX format. The processed data is transformed into an index and pushed to a newly created index in Azure Search. This tool streamlines the indexing process, making it easier to manage and search through relevant information.


## Requirements

- Python 3.10
- Azure Search Service
- Azure OpenAI
- Azure Storage Account (Optional)

## Installation

Set up Azure credentials:

Create a service principal in Azure and set the following environment variables in your .env file.
the variables where multiple values are accepted, the values need to be separated by "|"

```json
AZURE_SEARCH_SERVICE_ENDPOINT=<your-azure-search-endpoint>
AZURE_SEARCH_ADMIN_KEY=<your-azure-search-key>
AZURE_SEARCH_INDEX_NAME=<your-azure-search-index-name>

AZURE_OPENAI_API_KEY=<your-azure-openai-key>
AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>
AZURE_OPENAI_EMBEDDING_API_VERSION=<your-azure-openai-api-version>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<your-azure-openai-embedding-model-name>


AZURE_BLOB_ENDPOINT=<azure-storage-endpoint>
AZURE_BLOB_CONTAINER_NAME=<azure-storage-container-name> (or local folder when working without blob)
FOLDER_PATH=<path-to-push-the-index> (when running locally)

INDEX_VECTOR_COLUMNS=<name-of-content-to-be-embedded-columns> (ex: Libelle_Definition|Parents)
INDEX_MASTER_FILE_NAME=<name-of-master-data-file> (ex:Master_Data.xlsx)
INDEX_TTL_FILENAME_COLUMN=<name> (ex:ttl_filename)
INDEX_TAXO_NAME_COLUMN=<column-containing-name-of-taxo> (ex:Nom complet)
INDEX_TAXO_COLUMN=<column-containing-code-of-taxo> (ex:Taxonomie)
```

See env.sample for an example.

## Master File

The master file (`INDEX_MASTER_FILE_NAME`) is a crucial component of the app. This file contains all the columns that will become fields in the Azure Search index. Each row in the master file corresponds to one taxonomy in TTL format.

### Example Master File
|ttl_filename  | id  | Nom complet              | Nom raccourci      | Domaine	      | url |
| ------------ | --- | ------------------------ | ------------------ | -------------- | --- |
| taxo1.ttl    | 1   | EUROVOC................. | .................. | Generic....... | ... |
| taxo2.ttl    | 2   | NACE.................... | .................. | Sectorial..... | ... |
| taxo3.ttl    | 3   | NACE-BEL................ | .................. | Sectorial..... | ... |

## File Structure in folder or Azure Blob Container
```text
AZURE_BLOB_CONTAINER_NAME
|-- taxo1.ttl
|-- taxo2.ttl
|-- ...
|-- INDEX_MASTER_FILE_NAME (ex. Master_Data.xlsx)
```

## Application Functionality

### Overview

The application performs a series of distinct steps to effectively process and embed information from TTL files. The primary functionalities include reading a Master file, extracting data from TTLs, splitting the TTL  into concepts with their relevant semantic information (prefLabel, altLabel, definition, ...), and embedding these concepts.

### Steps

1. **Reading the Master File:**
   The application begins by reading the Master file, which serves as a central reference point. This file likely contains metadata and key information necessary for the subsequent steps in the process.

2. **Reading TTLs:**
   Following the Master file analysis, the application systematically reads the content of TTL files. Each TTL is a taxonomy containing valuable information that needs to be processed and embedded.

3. **Splitting TTL into concepts:**
   Once the TTL content is acquired, the application intelligently splits the taxonomy into manageable concepts with there relevant properties expressed in text. This segmentation ensures that information is organized and processed efficiently.

4. **Embedding concepts:**
   The core functionality involves embedding the taxonomy concepts into the system. This step likely involves encoding the information for future retrieval and analysis.
