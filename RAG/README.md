# Taxonomy maintenance chatbot

## Overview

The taxonomy maintenance chatbot is a Python application designed to support the maintenance and development of taxonomies using an Azure AI search index containing existing taxonomies and Azure OpenAI GPT. This tool allows to find information about existing taxonomies and quickly use it to update the taxonomy of the user.


## Requirements

- Python 3.10
- Azure Search Service
- Azure OpenAI

## Installation

Set up Azure credentials:

Create a service principal in Azure and set the following environment variables in your .env file.

```json
AZURE_OPENAI_ENDPOINT=<your-azure-open-ai-endpoint>
AZURE_OPENAI_GPT_DEPLOYMENT=<your-model-name>
AZURE_SEARCH_SERVICE_ENDPOINT<=your-azure-search-endpoint>
AZURE_SEARCH_ADMIN_KEY=<your-azure-search-api-key>
AZURE_SEARCH_INDEX_NAME=<your-azure-search-index-name>
AZURE_OPENAI_API_KEY=<your-azure-openai-api-key>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=<your-openai-embedding-model>
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG=<your-semantic-config>
AZURE_SEARCH_QUERY_TYPE=<choice-of-search-query-type>(ex: semantic)
AZURE_COGNITIVE_SEARCH_SERVICE_NAME=<your-azure-search-service-name>
OPENAI_API_VERSION=<your-azure-openai-version>


VECTOR_COLUMN=<name-of-the-vector-column-in-the-index> (ex: Libelle_Definition_vector)
```

See env.sample for an example.

## Launch the app locally

You can launch the app by running the following command:
```
streamlit run app.py
```
## Application Functionality

This application leverages Azure OpenAI and Azure Cognitive Search to assist users in semantic mapping and retrieving information about concepts from RDF taxonomies. The app provides functionalities for chatting with an AI assistant, mapping taxonomies, and generating SPARQL queries based on user inputs and RDF triples.

### Key Features
1. Semantic Mapping:
    - Extracts and processes RDF data to identify concept information.
    - Maps taxonomies based on user-provided labels and definitions.
    - Utilizes Azure Cognitive Search to find similar concepts and determine semantic relations.
2. Chatbot Interaction:
    - Provides a chatbot interface to assist users with semantic mappings and general inquiries.
    - Uses Azure OpenAI to generate responses and identify intents from user queries.
    - Supports conversation history to maintain context and improve interaction quality.

### How It Works
1. Initialization:
    - Load environment variables and initialize Azure OpenAI and Azure Cognitive Search clients.
2. Concept Information Extraction:
    - Extract labels, definitions, and related entities from RDF graphs using predefined SPARQL queries.
    - Join and concatenate extracted information to create structured documents.
3. Taxonomy Mapping:
    - Perform semantic searches using Azure Cognitive Search to find equivalent concepts.
    - Compare definitions and determine semantic relations (e.g., closeMatch, exactMatch).
4. Chatbot Functionality:
    - Handle user queries and maintain conversation history.
    - Generate responses using Azure OpenAI and provide relevant search results.
    - Identify user intents and suggest appropriate actions or mappings.

### Usage
1. Upload RDF Taxonomy: Import RDF data in TTL format to start a session.
2. Query and Map Taxonomies: Enter a concept or query to find equivalent concepts in the taxonomy. The chatbot assists by generating SPARQL queries and performing semantic searches.
3. Download Results: Export mapped taxonomies and search results in a structured format (Excel or JSON).