import os  
from openai import AzureOpenAI  

def chat_with_index(system_prompt, user_input, history, taxonomy_filter):
    """
    Chats with an Azure OpenAI model, incorporating search index data and semantic mappings.  
  
    :param system_prompt: The system prompt to guide the model's behavior.  
    :param user_input: The user's latest input for the chat.  
    :param history: The conversation history up until this point.  
    :param taxonomy_filter: The filter to apply to the taxonomy when querying the search index.  
    :return: The response content from the chat model. 
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://pwc138pocopenai-ai.openai.azure.com/")  
    deployment = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-4o")  
    search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT", "https://pwc-138-poc-openai-search.search.windows.net")  
    search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY", "put your Azure AI Search admin key here")  
    search_index = os.getenv("AZURE_SEARCH_INDEX_NAME", "search-index-v1")  
    subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "REPLACE_WITH_YOUR_KEY_VALUE_HERE")  

    # Initialize Azure OpenAI client with key-based authentication
    client = AzureOpenAI(  
        azure_endpoint=endpoint,  
        api_key=subscription_key,  
        api_version="2024-05-01-preview",  
    )  
        
    # Prepare the chat prompt  
    chat_prompt = [
            {"role": "system", "content": "You are a linguistic expert who helps the user find relevant information for semantic mappings"},
            {"role": "assistant", "content": f"The conversation history up until this point:\n{history}"},
            {"role": "user", "content": f"The user's latest input:\n{user_input}"}
    ]

    
    # Generate the completion  
    completion = client.chat.completions.create(  
        model=deployment,  
        messages=chat_prompt,  
        #past_messages=10,  
        max_tokens=800,  
        temperature=0,  
        top_p=0.95,  
        frequency_penalty=0,  
        presence_penalty=0,  
        stop=None,  
        stream=False,
        extra_body={
        "data_sources": [{
            "type": "azure_search",
            "parameters": {
            "endpoint": f"{search_endpoint}",
            "index_name": search_index,
            "semantic_configuration": os.getenv("AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG", "openai-poc-semantic-config"),
            "query_type": os.getenv("AZURE_SEARCH_QUERY_TYPE","semantic"),
            "fields_mapping": {
                "content_fields_separator": "\n",
                "content_fields": [
                "Libelle_Definition", "uri"
                ],
                "filepath_field": "uri",
                "title_field": "Taxonomie",
                "url_field": "uri",
                "vector_fields": [os.getenv("VECTOR_COLUMN", "Libelle_Definition_vector")]
            },
            "in_scope": True,
            "role_information": system_prompt,
            "filter": taxonomy_filter,
            "strictness": 3,
            "top_n_documents": 5,
            "authentication": {
                "type": "api_key",
                "key": f"{search_key}"
            },
            "embedding_dependency": {
              "type": "deployment_name",
              "deployment_name": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
            }
            }
        }]
        }   
        )

    response = completion.to_dict()
    print(response)

    return response["choices"][0]["message"]["content"]

def chat(system_prompt, user_input, history=""):
    """
    Chats with an Azure OpenAI model using the provided system prompt, user input, and conversation history.  
  
    :param system_prompt: The system prompt to guide the model's behavior.  
    :param user_input: The user's latest input for the chat.  
    :param history: The conversation history up until this point (default is an empty string).  
    :return: The response content from the chat model. 
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://pwc138pocopenai-ai.openai.azure.com/")  
    deployment = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-4o")  
    search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT", "https://pwc-138-poc-openai-search.search.windows.net")  
    search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY", "put your Azure AI Search admin key here")  
    search_index = os.getenv("AZURE_SEARCH_INDEX_NAME", "search-index-v1")  
    subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "REPLACE_WITH_YOUR_KEY_VALUE_HERE")   

    # Initialize Azure OpenAI client with key-based authentication
    client = AzureOpenAI(  
        azure_endpoint=endpoint,  
        api_key=subscription_key,  
        api_version="2024-05-01-preview",  
    )  
        
    # Prepare the chat prompt  
    chat_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": f"The conversation history up until this point: {history}"},
            {"role": "user", "content": f"The user's latest input:\n{user_input}"}
    ]

    
    # Generate the completion  
    completion = client.chat.completions.create(  
        model=deployment,  
        messages=chat_prompt,  
        #past_messages=10,  
        max_tokens=800,  
        temperature=0.2,  
        top_p=0.95,  
        frequency_penalty=0,  
        presence_penalty=0,  
        stop=None,  
        stream=False,
        )

    return completion.to_dict()["choices"][0]["message"]["content"]  