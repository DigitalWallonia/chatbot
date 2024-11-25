from rdflib import Graph, URIRef, Literal  
from rdflib.namespace import SKOS  
from collections import defaultdict  
from rdflib import ConjunctiveGraph, Graph
from rdflib.exceptions import ParserError
from urllib.parse import urlparse
from itertools import groupby
import pandas as pd
from dotenv import load_dotenv
import ast
import os
import re


from typing import Any, Dict, Iterable, Iterator, List, Optional

class ScrapingRDF():
    """
    A class to scrape and process RDF data.  
  
    This class provides methods to extract and process information from RDF graphs,  
    including extracting concept information, joining texts, concatenating information,  
    and scraping RDF datasets.  
  
    Methods:  
    - __init__: Initializes the ScrapingRDF instance.  
    - extract_concept_info: Extracts information about a concept from the RDF graph.  
    - join_texts: Joins texts from a dictionary based on specified languages.  
    - concatenate_info: Concatenates the extracted concept information into a document.  
    - ScrapeRDF: Scrapes RDF data and builds a knowledge base. 
    """
    def __init__(self) -> None:
        pass

    def extract_concept_info(self, graph, concept_uri): 
        """
        Extracts information about a concept from the RDF graph.  
  
        :param graph: The RDF graph to extract information from.  
        :param concept_uri: The URI of the concept to extract information for.  
        :return: A dictionary containing the extracted concept information.  
        """ 
        concept = URIRef(concept_uri)  
        
        def get_labels_and_definitions(predicate):  
            labels = {}  
            for obj in graph.objects(concept, predicate):  
                if isinstance(obj, Literal):  
                    lang = obj.language if obj.language else 'default'  
                    if lang not in labels:  
                        labels[lang] = []  
                    labels[lang].append(str(obj))  
            return labels  
        
        pref_labels = get_labels_and_definitions(SKOS.prefLabel)  
        alt_labels = get_labels_and_definitions(SKOS.altLabel)  
        definitions = get_labels_and_definitions(SKOS.definition)  
        
        related_entities = list(graph.objects(concept, SKOS.related))  
        broader_entities = list(graph.objects(concept, SKOS.broader))  
        narrower_entities = list(graph.objects(concept, SKOS.narrower))  
        
        def get_related_labels(entities):  
            related_labels = {}  
            for entity in entities:  
                for obj in graph.objects(entity, SKOS.prefLabel):  
                    if isinstance(obj, Literal):  
                        lang = obj.language if obj.language else 'default'  
                        if lang not in related_labels:  
                            related_labels[lang] = []  
                        related_labels[lang].append(str(obj))  
            return related_labels

        related_entities_labels = get_related_labels(related_entities)  
        broader_entities_labels = get_related_labels(broader_entities)  
        narrower_entities_labels = get_related_labels(narrower_entities)

        # Extract triples linked to the concept  
        linked_triples = list(graph.triples((concept, None, None)))
        linked_triples_str = " ".join([f"{s} {p} {o}" for s, p, o in linked_triples])  
    

        return {  
            "pref_labels": pref_labels,  
            "alt_labels": alt_labels,  
            "definitions": definitions,  
            "related_entities_labels": related_entities_labels,  
            "broader_entities_labels": broader_entities_labels,  
            "narrower_entities_labels": narrower_entities_labels, 
            "linked_triples": linked_triples_str 
        }
    
    def join_texts(self, texts_dict):  
        """
        Joins texts from a dictionary based on specified languages.  
  
        :param texts_dict: A dictionary containing texts in different languages.  
        :return: A combined list of texts for the specified languages. 
        """
        combined_text = []  
        for lang in ['en', 'fr', 'default']:  # Specify the languages you want to combine  
            combined_text.extend(texts_dict.get(lang, []))  
        return combined_text

    def concatenate_info(self, concept_info, concept_uri, taxonomie, id, lang='default'): 
        """
        Concatenates the extracted concept information into a document.  
  
        :param concept_info: The extracted concept information.  
        :param concept_uri: The URI of the concept.  
        :param taxonomie: The taxonomy to which the concept belongs.  
        :param id: The ID of the concept.  
        :param lang: The language for the text (default: 'default').  
        :return: A tuple containing the document dictionary and the full text.  
        """
        label = "/".join(self.join_texts(concept_info["pref_labels"]))  
        altlabel = " (ou {})".format(", ".join(self.join_texts(concept_info["alt_labels"]))) if (concept_info["alt_labels"].get(lang, []) or concept_info["alt_labels"].get("fr", []) or concept_info["alt_labels"].get('default', [])) else ""  
        defi = " : {}.".format("".join(self.join_texts(concept_info["definitions"]))) if (concept_info["definitions"].get(lang, []) or concept_info["definitions"].get("fr", []) or concept_info["definitions"].get('default', [])) else ""  
        related = "\nConcepts liés à {}: {}.".format(label, "; ".join(self.join_texts(concept_info["related_entities_labels"]))) if (concept_info["related_entities_labels"].get(lang, []) or concept_info["related_entities_labels"].get("fr", []) or concept_info["related_entities_labels"].get('default', [])) else ""
        narrow = "\n{} est un concept plus large que: {}.".format(label, "; ".join(self.join_texts(concept_info["narrower_entities_labels"]))) if (concept_info["narrower_entities_labels"].get(lang, []) or concept_info["narrower_entities_labels"].get("fr", []) or concept_info["narrower_entities_labels"].get('default', [])) else "" 
        broad = "\n{} est un concept plus étroit ou une sous-classe de: {}.".format(label, "; ".join(self.join_texts(concept_info["broader_entities_labels"]))) if (concept_info["broader_entities_labels"].get(lang, []) or concept_info["broader_entities_labels"].get("fr", []) or concept_info["broader_entities_labels"].get('default', [])) else ""  

        document = {
                        "subject": "{}".format(concept_uri),
                        "prefLabel": "{}".format(label),
                        "definition": "{}".format(altlabel + defi + related + narrow + broad),
                    }
        
        full_text = label + altlabel + defi + related + narrow + broad

        return document, full_text 

    def ScrapeRDF(self, g, KnowledgeBase):
        """
        Scrapes RDF data and builds a knowledge base.  
  
        :param g: The RDF graph to scrape.  
        :param KnowledgeBase: A list to which the extracted documents will be appended.  
        :return: The updated knowledge base with the extracted documents.  
        """
        concept_uris = set(g.subjects(predicate=SKOS.prefLabel))  
        KnowledgeBase = []

        id = 1

        for concept_uri in concept_uris:  
            concept_info = self.extract_concept_info(g, concept_uri)  
            document, combined_text = self.concatenate_info(concept_info, concept_uri, "ttl", id, lang='en')
            KnowledgeBase.append(document)
            print(combined_text)

            id += 1

        return KnowledgeBase
