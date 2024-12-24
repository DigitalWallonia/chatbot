from io import BytesIO
import streamlit as st
import rdflib
import pandas as pd
from utils.RDF import ScrapingRDF

def _get_concepts_as_table(graph):
    """
    Retrieves concepts from an RDF graph and returns them as a pandas DataFrame.  
  
    :param graph: The RDF graph from which to retrieve concepts.  
    :return: A pandas DataFrame containing the concepts and their annotations.  
    """
    data = ScrapingRDF().ScrapeRDF(graph, []) #[]  

  # Create a pandas DataFrame from the list of dictionaries  
    return pd.DataFrame(data)

def import_ttl(uploaded_file):
    """
    Imports a TTL file, parses it as an RDF graph, and retrieves the concepts as a pandas DataFrame.  
  
    :param uploaded_file: The uploaded TTL file to be imported.  
    :return: A tuple containing the parsed RDF graph and a pandas DataFrame with the concepts.  
    """
    bytes_data = BytesIO(st.session_state["uploaded_file"].read())

    g = rdflib.Graph()
    taxonomy_data = g.parse(bytes_data, format="ttl")
    pandas_data = _get_concepts_as_table(g)
    print(pandas_data)

    st.session_state["namespace"] = "namespace"
    
    return taxonomy_data, pandas_data

