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

from RAG.agents.research_agent import build_and_test_graph as build_research_graph
from RAG.agents.taxonomy_agent import build_and_test_graph as taxonomy_graph

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


# Graph Nodes
@tool
def chat(user_query: str, conversation_history: str) -> str:
    """
    Use all the available information to provide an answer to the user's query.

    :param state: The current state of the conversation.
    :return: Updated state with AI's response.
    """
    messages = [
        {"role": "system", "content": "Use the following information to answer the last user query:"},
        {"role": "assistant", "content": f"The conversation history up until this point:\n{conversation_history}"},
        {"role": "user", "content": f"The user's latest input:\n{user_query}"},
    ]
    final_response = llm.invoke(messages)
    return final_response.content

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
    workers = ["research_team", "taxo_team", "chat"]

    system_prompt = system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        f" following workers: {workers}. The workers specialize in different tasks:"
        "\n- `research_team`: Looks for information in a search index and on the web. Can also chat with the user"
        "\n- `taxo_team`: Modify the taxonomy of the user."
        "\n- `chat`: Use the information provided by the workers to generate a final answer to the user."
        "\n- `FINISH`: Concludes the process if sufficient information is available to"
        " address the user's query."
        "\n\nYour task is to analyze the user's request and decide the next worker to call."
        "\n- If the user explicitly asks to search something (or wants to chat), route to `research_team`."
        "\n- If the user explicitly asks to remove, add, or modify concepts from the taxonomy, route to `taxo_team`."
        "\n- If the first worker did not provide sufficient information, route to the other one."
        "\n- If the user simply wants to chat or when you believe all the necessary information is available, route to `chat`."
        "\n- If the user's request is fully addressed, route to `FINISH`."
        "\n\nAlways respond with the name of the next worker to act. Do not perform any"
        " tasks yourself. Never route twice to the same worker"
    )

    # Define worker nodes
    teams_supervisor_node = make_supervisor_node(llm, ["research_team", "taxo_team", "chat"], system_prompt)

    research_graph = build_research_graph()
    taxo_modifier_graph = taxonomy_graph()
    chat_agent = create_react_agent(llm, tools=[chat])

    def chat_node(state: AgentState) -> AgentState:
        result = chat_agent.invoke(state)
        return {"messages": [AIMessage(content=result["messages"][-1].content, name="chat")]}

    def call_research_team(state: AgentState) -> AgentState:
        response = research_graph.invoke({"messages": state["messages"][-1]})
        return {"messages": [HumanMessage(content=response["messages"][-1].content, name="research_team")]}


    def call_paper_writing_team(state: AgentState) -> AgentState:
        response = taxo_modifier_graph.invoke({"messages": state["messages"][-1]})
        return {"messages": [HumanMessage(content=response["messages"][-1].content, name="taxo_team")]}


    # Define the graph.
    super_builder = StateGraph(AgentState)
    super_builder.add_node("supervisor", teams_supervisor_node)
    super_builder.add_node("research_team", call_research_team)
    super_builder.add_node("taxo_team", call_paper_writing_team)
    super_builder.add_node("chat", chat_node)
    super_builder.add_edge(START, "supervisor")
    super_builder.add_edge("research_team", "supervisor")
    super_builder.add_edge("taxo_team", "supervisor")
    super_builder.add_edge("chat", END)
    super_builder.add_conditional_edges("supervisor", lambda state: state["next"])
    
    return super_builder.compile()