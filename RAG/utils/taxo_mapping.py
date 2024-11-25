from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType
from utils.chat_functions import chat, chat_with_index 
import rdflib
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Azure OpenAI  
client = AzureOpenAI(api_key=os.environ.get("AZURE_OPENAI_API_KEY"))

# Initialize Azure Cognitive Search Client  
search_service = os.environ.get("AZURE_COGNITIVE_SEARCH_SERVICE_NAME")  
index_name = os.environ.get("AZURE_SEARCH_INDEX_NAME")  
search_api_key = os.environ.get("AZURE_SEARCH_ADMIN_KEY")  
search_client = SearchClient(endpoint=f"https://{search_service}.search.windows.net",  
                             index_name=index_name,  
                             credential=AzureKeyCredential(search_api_key))  
  
def libelle_definition_split(libelle_definition):
    """
    Splits a libelle definition into a label and definition.  
  
    :param libelle_definition: The libelle definition to be split.  
    :return: A tuple containing the label and definition.
    """
    parts = libelle_definition.split(':', 1)
    
    if len(parts) == 2:
        # Further split the first part to separate the label from altlabels  
        label_part = parts[0].strip()  
        definition = parts[1].strip() 

        # Extract the label before the first '('  
        label = label_part.split('(', 1)[0].strip() 
    else: 
        label = parts[0].split('(', 1)[0].strip()
        definition = ""

    return label, definition

def mapping_confidence_split(mapping):
    """
    Splits a mapping into a SKOS relation and confidence score.  
  
    :param mapping: The mapping to be split.  
    :return: A tuple containing the SKOS relation and confidence score.
    """
    parts = mapping.split('(', 1)
    
    maps = "skos:" + parts[0] 
    confidence = parts[1].split(')', 1)[0].strip()

    return maps, confidence

def _search_taxonomies(concept_label, concept_definition, taxonomy_filter=None):  
    """
    Searches for taxonomies in the Azure Cognitive Search index based on a concept label and definition.  
  
    :param concept_label: The label of the concept to search for.  
    :param concept_definition: The definition of the concept to search for.  
    :param taxonomy_filter: An optional filter to apply to the taxonomy search.  
    :return: The search results from the Azure Cognitive Search index.
    """
    if concept_definition is not None:
        search_query = f"{concept_label}{concept_definition}"
    else: 
        search_query = f"{concept_label} "

    if taxonomy_filter is None:  
        #results = search_client.search(search_query, top=5)
        vector_query = VectorizableTextQuery(text=search_query, k=5, fields="Libelle_Definition_vector", exhaustive=True)
        results = search_client.search(  
                                            search_text=search_query,  
                                            vector_queries=[vector_query],
                                            #filter=filter_condition,
                                            select=["uri", "Libelle_Definition"],
                                            query_type=QueryType.SEMANTIC, semantic_configuration_name='openai-poc-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
                                            top=5
                                        )
    else:
        filter_condition = f"Taxonomie eq '{taxonomy_filter}'"        
        #results = search_client.search(search_query, top=5, filter=filter_condition)
        vector_query = VectorizableTextQuery(text=search_query, k=5, fields="Libelle_Definition_vector", exhaustive=True)
        results = search_client.search(  
                                            search_text=search_query,  
                                            vector_queries=[vector_query],
                                            filter=filter_condition,
                                            select=["uri", "Libelle_Definition"],
                                            query_type=QueryType.SEMANTIC, semantic_configuration_name='openai-poc-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
                                            top=5
                                        )
    return results  
  
def _compare_definitions(prompt):      
    """
    Compares concept definitions using the Azure OpenAI model.  
  
    :param prompt: The prompt to send to the Azure OpenAI model for comparison.  
    :return: The comparison result from the Azure OpenAI model.
    """
    completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Hello ! You are a linguistic expert who understands the semantic relationships between concepts that helps me with semantic mappings"},
                {"role": "user", "content": prompt}
            ]
    )
    
    print(completion.choices[0].message.content)
    return completion.choices[0].message.content.strip()  
  
def _find_similar_concepts(user_label, user_definition, user_uri, taxonomy_filter, j):  
    """
    Finds similar concepts in the Azure Cognitive Search index based on a user-provided label and definition.  
  
    :param user_label: The label of the user-provided concept.  
    :param user_definition: The definition of the user-provided concept.  
    :param user_uri: The URI of the user-provided concept.  
    :param taxonomy_filter: An optional filter to apply to the taxonomy search.  
    :param j: The current index for mapping URIs.  
    :return: A tuple containing the similar concepts and the updated index.
    """
    print(user_label)
    search_results = list(_search_taxonomies(user_label, user_definition, taxonomy_filter))   
    length = len(search_results)
    matches = [] 
    labels = []

    if length == 0:
        print("here2")
        return []
    
    for i, result in enumerate(search_results):
        print(result)  
        labels.append(f"Concept {i+2}: " + result['Libelle_Definition'])
        label, definition = libelle_definition_split(result['Libelle_Definition'])
        matches.append({  
            'URI': "",
            'rdf:type': "align:cell",
            'align:entity1': result['uri'],
            'URI ': result['uri'],
            'skos:prefLabel': label, 
            'skos:definition': definition,   
            'align:relation': "",
            'align:measure^^xsd:float': "",
            'owl:annotatedProperty': "",
            'skos:prefLabel ': user_label,
            'skos:definition ': user_definition,
            'align:entity2': user_uri, 
            'URI  ': user_uri,   
        })
        print(labels)
        
    prompt = """
Your task is to compare the following concepts and determine  the most appropriate semantic relation, i.e., if they are a SKOS closeMatch, exactMatch, or none.

You should only compare Concept 1 to all the other concepts. For each pair, provide only the type of match (exactMatch, closeMatch, or none) as well as a confidence score from 0 to 1.

Be aware that each concept can be described by: Label (list of alternative labels) and Definition. These can be provided in different languages, but this should not affect the mapping. Focus solely on the semantic meaning to determine the match type.

Please provide the results only in the following format: ["Chosen mapping (score)", "Chosen mapping (score)", ...].

Concept 1:
Label (alternative labels): {}
Definition: {}

Concepts to compare:
{}

Response:
""".format(user_label, user_definition, "\n".join(labels))  
    
    comparison_result = _compare_definitions(prompt)
    results = []

    for mapping, match in zip(eval(comparison_result), matches):
        # Parse the GPT response (assuming it's structured in some way)
        print(match)  
        if "closematch" in mapping.lower() or "exactmatch" in mapping.lower():  
            match["align:relation"] = "="
            match["owl:annotatedProperty"], match["align:measure^^xsd:float"] = mapping_confidence_split(mapping)
            match["URI"] = "mapping:cell/" + str(j)
            
            results.append(match)
            j = j + 1
        
    return results, j  

def mapping_taxonomies(user_label, user_definition, user_uri, j, taxonomy_filter=None, loop=False):   
    """
    Maps taxonomies based on user-provided labels and definitions.  
  
    :param user_label: The label of the user-provided concept.  
    :param user_definition: The definition of the user-provided concept.  
    :param user_uri: The URI of the user-provided concept.  
    :param j: The current index for mapping URIs.  
    :param taxonomy_filter: An optional filter to apply to the taxonomy search.  
    :param loop: A boolean to indicate if the mapping should loop.  
    :return: A tuple containing the similar concepts and the updated index or a formatted string.  
    """
    similar_concepts, j = _find_similar_concepts(user_label, user_definition, user_uri, taxonomy_filter, j)  
    
    if loop:
        #TO DO
        return similar_concepts, j
    else:
        answer = []
        for concept in similar_concepts:  
            answer.append("{} - {} - {} ({})".format(user_label, concept["mapping"], concept["label"], concept["uri"]))

        return "\n".join(answer)
    
def _identify_intent(user_input, history):
    """
    Identifies the main concept of interest from the user's query based on the query and conversation history.  
  
    :param user_input: The user's query.  
    :param history: The conversation history.  
    :return: The identified concept.
    """
    system_prompt = f"""  
    Identify the main concept of interest from the last user's query based on the query and the conversation history. For example, if the user asks "Peux-tu me trouver un concept équivalent à Aerodrome?", extract "Aerodrome" as the concept for the search. The concept should always be limited to one word (only return one word). 
    
    If necessary to make the semantic meaning of the concept clear, you can also provide a synonym or a translation (either in french or english). Then return a list ["concept", "synonym or translation"]  
    """
    concept = chat(system_prompt, user_input, history)

    return concept

def _generating_sparql(user_input, history):
    
    concept = _identify_intent(user_input, history)

    query = f"""  
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>    
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>  

    SELECT ?s
    WHERE {{  
        ?s (skos:prefLabel|skos:altLabel) ?label .
        FILTER(?label = "{concept}"@en || ?label = "{concept}"@fr || ?label = "{concept}"@en)  

    }}    
    """ 
    return query, concept

def _generating_search_query(user_input, triples, history, taxonomy_filter):
    """
    Generates a search query based on the user's query, conversation history, and RDF triples.  
  
    :param user_input: The user's query.  
    :param triples: The RDF triples providing additional semantic information about the concept.  
    :param history: The conversation history.  
    :param taxonomy_filter: An optional filter to apply to the taxonomy search.  
    :return: The generated search query.  
    """
    triples = str(triples.serialize(format="ttl"))
    
    system_prompt = f"""Identify the main concept of interest from the last user's query based on the query, the conversation history, and a set of RDF triples bringing additional semantic information about the concept. The concept should always be limited to one or two words (only return one/two word).
    
    If necessary to make the semantic meaning of the concept clear, you can also provide a synonym or a translation (either in french or english). Then return "concept", "synonym or translation"  
    """  

    
    prompt = f""" 
    Conversation history: "{history}" 
    Related triples: {triples}

    User's concept: "{user_input}"
    """
    question = chat(system_prompt, prompt)

    return question


def chatting_and_mapping_taxonomies(user_input, taxonomy, taxonomy_filter=None, history=""):   
    """
    Facilitates chatting and mapping taxonomies based on user input, taxonomy, and conversation history.  
  
    :param user_input: The user's input for the chat.  
    :param taxonomy: The taxonomy to be used for mapping.  
    :param taxonomy_filter: An optional filter to apply to the taxonomy search.  
    :param history: The conversation history (default is an empty string).  
    :return: The response from the chat function.
    """
    #1° Generate appropriate SPARQL query
    # query = _generating_sparql(user_input, history)
    # try:
    #     #2° Query the taxonomy for triples
    #     for result in taxonomy.query(query[0]):
    #         triples = taxonomy.query(f"DESCRIBE <{result.s}>")
    #         break 
    #     #Design an appropriate search query
    #     search_query = _generating_search_query(query[1], triples, history, taxonomy_filter)
    #     print("here")
    # except:
    #     # If the SPARQL query does not work, just perform a research based on the user request
    #     search_query =f"""Search intent (only search these words): {_identify_intent(user_input, history)}""" 
    # #4° Search and answer the question
    # print(search_query)
    system_prompt = f"""
    You are a chatbot designed to assist users with semantic mappings. Users will describe a concept, and your task is to find if there is an equivalent concept in an Azure AI search index. The index contains documents, each describing one concept by its label, alternative labels, and definition. If an equivalent concept is found, provide the relevant document's "uri" field as a reference.

    If the user's intent is not to find an equivalent concept or if no relevant document is found in the index, your answer should always be the following (do not translate!!!): "The requested information is not available in the retrieved data. Please try another query or topic.".
    """
    # Here is the user's question: {user_input}
    #"""
    #"You are a linguistic expert who helps the user find relevant information for semantic mappings between concepts. Be aware that labels, alternative labels, and definitions of documents from the index can be provided in different languages. This should not affect the mapping; focus only on the semantic meaning. When answering, always provide the labels, definitions (Libelle_Definition), and uri of the retrieved concepts. If possible, suggest a SKOS mapping. Always respond in the same language as the user."  
    if taxonomy_filter is None:  
        filter_condition = None
    else:
        filter_condition = f"Taxonomie eq '{taxonomy_filter}'"        
    
    response = chat_with_index(system_prompt, user_input, history, filter_condition)
    print(response)
    if response == "The requested information is not available in the retrieved data. Please try another query or topic." or response == "Les informations demandées ne sont pas disponibles dans les données récupérées. Veuillez essayer une autre requête ou un autre sujet.":
        
        system_prompt = f"""
    You are a chatbot designed to assist users with semantic mappings and answer its questions. You might face two types of questions:
    1° The user wants to find similar concepts to the one they are describing. Then your task is to find an equivalent concept. Use your own knowledge and the conversation history to provide an answer. In that case, always begin your answer with (translated in the language of the user): I could not find relevant concepts in the index, but based on my own knowledge here are concepts that could be similar to {{user's concepts}}: {{your answer}}"

    2° The user's intent is not to find an equivalent concept but simply to chat with you. Then, simply use your own knowledge and the conversation history to provide an answer.
    """
        
        response = chat(system_prompt, user_input, history)
    
    return response