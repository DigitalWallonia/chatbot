import os
import logging
from typing import Annotated, List, Literal, TypedDict, Optional

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
def scrape_webpages(queries: List[str]) -> str:
    """
    Perform web scraping using the DuckDuckGo search engine.

    :param queries: List of user queries to search on the web.
    :return: Aggregated results as a string.
    """
    wrapper = DuckDuckGoSearchAPIWrapper(max_results=2)
    answer = []

    for query in queries:
        search = DuckDuckGoSearchResults(api_wrapper=wrapper, output_format="list")
        results = search.invoke(query)
        answer.append("\n\n".join(
        [f'<Document name="{doc["title"]}">\n{doc["snippet"]}\n</Document>' for doc in results]
        ))

    return "\n\n".join(answer)


@tool
def search_index(search_query: str, taxonomy_filter: str) -> str:
    """
    Searches for taxonomies in the Azure Cognitive Search index based on a concept label and definition.  
  
    :param search_query: the search query of the user 
    :param taxonomy_filter: An optional filter to apply to the taxonomy search.  
    :return: The search results from the Azure Cognitive Search index.
    """
    logging.info(search_query)

    if taxonomy_filter is None:  
        #results = search_client.search(search_query, top=5)
        vector_query = VectorizableTextQuery(text=search_query, k_nearest_neighbors=5, fields="Libelle_Definition_vector", exhaustive=True)
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
        vector_query = VectorizableTextQuery(text=search_query, k_nearest_neighbors=5, fields="Libelle_Definition_vector", exhaustive=True)
        results = search_client.search(  
                                            search_text=search_query,  
                                            vector_queries=[vector_query],
                                            filter=filter_condition,
                                            select=["uri", "Libelle_Definition"],
                                            query_type=QueryType.SEMANTIC, semantic_configuration_name='openai-poc-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,
                                            top=5
                                        )
    
    search_results = []
    for i, result in enumerate(list(results)):
        print(result)  
        search_results.append(f'<Document name="{result["uri"]}">\n{result["Libelle_Definition"]}\n{result["Parents"]}\n</Document>')
        print("\n\n".join(search_results))
    return "\n\n".join(search_results)  


# Graph Nodes
@tool
def summarise_and_answer(user_query: str, conversation_history: str) -> str:
    """
    Summarize conversation history and answer the user's query.

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
    workers = ["search", "web_scraper", "summarise"]
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        f" following workers: {workers}. The workers specialize in different tasks:"
        "\n- `search`: Performs a search query on structured data or databases."
        "\n- `web_scraper`: Scrapes data directly from the web for user queries requiring"
        " web content."
        "\n- `summarise`: Generate an answer for the user based on the conversation history (including the results of the work of the other workers)"
        "\n- `FINISH`: Concludes the process if sufficient information is available to"
        " address the user's query."
        "\n\nYour task is to analyze the user's request and decide the next worker to call."
        "\n- If the user explicitly asks to scrape the web or mentions data not available"
        " through structured search, route to `web_scraper`."
        "\n- If the user needs general structured information, route to `search`."
        "\n- If the first of these two workes did not provide sufficient information, route to the other one."
        "\n- If the user is simply chatting or if you want to summarise the work of the other workers, route directly to `summarise` and then `FINISH`."
        "\n- If the user's request is fully addressed, route to `FINISH`."
        "\n\nAlways respond with the name of the next worker to act. Do not perform any"
        " tasks yourself. Never route twice to the same worker"
    )

    # Define worker nodes
    search_agent = create_react_agent(llm, tools=[search_index])
    web_scraper_agent = create_react_agent(llm, tools=[scrape_webpages])
    summarise_agent = create_react_agent(llm, tools=[summarise_and_answer])

    def search_node(state: AgentState) -> AgentState:
        result = search_agent.invoke(state)
        return {"messages": [AIMessage(content=result["messages"][-1].content, name="search")]}

    def web_scraper_node(state: AgentState) -> AgentState:
        result = web_scraper_agent.invoke(state)
        return {"messages": [AIMessage(content=result["messages"][-1].content, name="web_scraper")]}
    
    def summarise_node(state: AgentState) -> AgentState:
        result = summarise_agent.invoke(state)
        return {"messages": [AIMessage(content=result["messages"][-1].content, name="summarise")]}

    # Build graph
    supervisor_node = make_supervisor_node(llm, workers, system_prompt)
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("supervisor", supervisor_node)
    graph_builder.add_node("search", search_node)
    graph_builder.add_node("web_scraper", web_scraper_node)
    graph_builder.add_node("summarise", summarise_node)
    graph_builder.add_edge(START, "supervisor")
    graph_builder.add_edge("search", "supervisor")
    graph_builder.add_edge("web_scraper", "supervisor")
    graph_builder.add_edge("summarise", END)
    graph_builder.add_conditional_edges("supervisor", lambda state: state["next"])

    return graph_builder.compile()