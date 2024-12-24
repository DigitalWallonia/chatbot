import os
import logging
from typing import Annotated, List, Literal, TypedDict, Optional
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional
from rdflib import Graph, RDF, SKOS
from rdflib import Literal as LiteralRDF
from rdflib.term import URIRef

from langchain_experimental.utilities import PythonREPL
from typing_extensions import TypedDict

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizableTextQuery,
    QueryType,
    QueryCaptionType,
    QueryAnswerType,
)
from langchain_community.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import create_react_agent
import streamlit as st

# Load environment variables
load_dotenv()

# Global constants for Azure Cognitive Search configuration
SEARCH_SERVICE = os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize clients
llm = AzureChatOpenAI(api_key=AZURE_OPENAI_API_KEY, model="gpt-4o")
search_client = SearchClient(
    endpoint=f"https://{SEARCH_SERVICE}.search.windows.net",
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(SEARCH_API_KEY),
)

# Tools
@tool
def get_args():

    return "tset"


@tool
def add_to_taxonomy(
    namespace: Annotated[str, "The namespace of the user's taxonomy to be used to construct uri"],
    concept: Annotated[str, "The concept to be added to the taxonomy"],
    prefLabel_fr: Annotated[str, "The french label of the concept to be added to the taxonomy (if none should be equal to '')"],
    prefLabel_en: Annotated[str, "The english label of the concept to be added to the taxonomy (if none should be equal to '')"],
    altLabels_en: Annotated[List[str], "A list of english alternative labels of the concept to be added to the taxonomy (if none should be equal to '')"],
    altLabels_fr: Annotated[List[str], "A list of french alternative labels of the concept to be added to the taxonomy (if none should be equal to '')"],
    definition_fr: Annotated[str, "French definition of the concept to be added (if none should be equal to '')"],
    definition_en: Annotated[str, "English definition of the concept to be added (if none should be equal to '')"],
    parent: Annotated[str, "The uri of the broader concept to which the user's concept needs to be linked (if none should be equal to '')"],
) -> Annotated[str, "Path of the saved outline file."]:
    """Add a concept to the taxonomy of the user based on the conversation's history"""
    namespace = st.session_state["namespace"]
    uri = namespace + concept
    print(uri)

    taxonomy = st.session_state["ttl_data"][0]  

    taxonomy.add((URIRef(uri), RDF.type, SKOS.Concept))
    taxonomy.add((URIRef(uri), SKOS.broader, URIRef(parent)))
    print(prefLabel_fr)
    taxonomy.add((URIRef(uri), SKOS.prefLabel, LiteralRDF(prefLabel_fr, lang="fr")))
    taxonomy.add((URIRef(uri), SKOS.prefLabel, LiteralRDF(prefLabel_en, lang="en")))
    taxonomy.add((URIRef(uri), SKOS.definition, LiteralRDF(definition_fr, lang="fr")))
    taxonomy.add((URIRef(uri), SKOS.definition, LiteralRDF(definition_en, lang="en")))
    for altLabel_en, altLabel_fr in zip(altLabels_en, altLabels_fr):
        taxonomy.add((URIRef(uri), SKOS.altLabel, LiteralRDF(altLabel_fr, lang="fr")))
        taxonomy.add((URIRef(uri), SKOS.altLabel, LiteralRDF(altLabel_en, lang="en")))
    
    st.session_state["ttl_data"][0] = taxonomy
    
    return f"Changes made to taxonomy"

@tool
def remove_from_taxo(
    taxonomy: Annotated[str, "The taxonomy to be modified"],
    namespace: Annotated[str, "The namespace of the user's taxonomy to be used to construct uri"],
    concept: Annotated[str, "The concept to be removed from the taxonomy"],
):
    """Remove a concept from the taxonomy of the user based on the conversation's history"""
    concept_uri = namespace + concept
    # Convert the concept URI to a URIRef  
    concept = URIRef(concept_uri)  
      
    # Remove all triples where the concept is the subject  
    for s, p, o in taxonomy.triples((concept, None, None)):  
        taxonomy.remove((s, p, o))  
      
    # Optionally, remove all triples where the concept is the object  
    for s, p, o in taxonomy.triples((None, None, concept)):  
        taxonomy.remove((s, p, o))  

    return f"Changes made to taxonomy"

# The agent state is the input to each node in the graph
class AgentState(MessagesState):
    # The 'next' field indicates where to route to next
    next: str

def make_supervisor_node(llm: BaseChatModel, members: list[str], system_prompt: tuple[str]) -> str:
    options = ["FINISH"] + members
    """
    Create a supervisor node for managing workers and routing tasks.

    :param llm: The language model used for decision-making.
    :param workers: List of available worker tools.
    :param system_prompt: Instructions for the supervisor.
    :return: Supervisor node function.
    """

    class Router(TypedDict):
        """Worker to route to next. If no workers needed, route to FINISH."""
        next: Literal[tuple(options)]

    def supervisor_node(state: MessagesState) -> MessagesState:
        messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        response = llm.with_structured_output(Router).invoke(messages)

        next_ = response["next"]
        if next_ == "FINISH":
            next_ = END

        return {"next": next_}

    return supervisor_node


# Test Graph
def build_and_test_graph():
    """
    Build and test a state graph with supervisor and workers.

    :return: Compiled graph for execution.
    """
    workers = ["add_to_taxo", "remove_from_taxo"]

    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        f" following workers: {workers}. The workers specialize in different tasks:"
        "\n- `add_to_taxo`: Add new triples to an RDF document based on provided information."
        "\n- `remove_from_taxo`: Remove triples from an RDF document based on provided information."
        "\n- `FINISH`: Concludes the process if sufficient information is available to"
        " address the user's query."
        "\n\nYour task is to analyze the user's request and decide the next worker to call."
        "\n- If the user explicitly asks to add new concepts to the taxonomy, route to `add_to_taxo`."
        "\n- If the user explicitly asks to remove concepts from the taxonomy, route to `remove_from_taxo`."
        "\n- If the first worker did not provide sufficient information, route to the other one."
        "\n- If the user's request is fully addressed, route to `FINISH`."
        "\n\nAlways respond with the name of the next worker to act. Do not perform any"
        " tasks yourself."
    )

    # Define worker nodes
    add_taxo_agent = create_react_agent(llm, tools=[add_to_taxonomy])
    remove_taxo_agent = create_react_agent(llm,tools=[remove_from_taxo])

    def add_taxo_node(state: AgentState) -> AgentState:
        result = add_taxo_agent.invoke(state)
        return {"messages": [HumanMessage(content=result["messages"][-1].content, name="add_to_taxo")]}

    def remove_taxo_node(state: AgentState) -> AgentState:
        result = remove_taxo_agent.invoke(state)
        return {"messages": [HumanMessage(content=result["messages"][-1].content, name="remove_from_taxo")]}

    # Build graph
    supervisor_node = make_supervisor_node(llm, ["add_to_taxo", "remove_from_taxo"], system_prompt)
    # Create the graph here
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("supervisor", supervisor_node)
    graph_builder.add_node("add_to_taxo", add_taxo_node)
    graph_builder.add_node("remove_from_taxo", remove_taxo_node)
    graph_builder.add_edge(START, "supervisor")
    graph_builder.add_edge("add_to_taxo", "supervisor")
    graph_builder.add_edge("remove_from_taxo", "supervisor")
    graph_builder.add_conditional_edges("supervisor", lambda state: state["next"])

    return graph_builder.compile()