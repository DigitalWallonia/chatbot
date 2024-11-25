# Import relevant libraries
import os
import re
import numpy as np
from openai import AzureOpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt

from dotenv import load_dotenv

load_dotenv(override=True)

AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_API_VERSION"
)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")


def _normalize_text(s):
    """
    This function performs various text normalization tasks such as removing  
    multiple spaces, replacing certain characters, and stripping leading/trailing spaces.  
  
    :param s: The input text to be normalized.  
    :return: The normalized text.
    """
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r". ,", "", s)
    # remove all instances of multiple spaces
    s = s.replace("..", ".")
    s = s.replace(". .", ".")
    s = s.replace("\n", "")
    s = s.strip()
    return s


@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(3))
def _get_embedding(text: str) -> list:
    """
    Retrieve the embedding for the given text using the Azure OpenAI API. This function uses the Azure OpenAI API to generate embeddings for the input text.  
    It retries the request with exponential backoff in case of failure.  
  
    :param text: The text to retrieve the embedding for.  
    :return: The embedding for the given text.  
    """
    try:
        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_EMBEDDING_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )

        response = client.embeddings.create(
            input=text, model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        )
        return response.data[0].embedding

    except Exception as e:
        raise Exception(
            f"Error getting embeddings with endpoint={AZURE_OPENAI_ENDPOINT} with error={e} for text={text}"
        )


def text_to_embedding(text: str) -> list:
    """
    Retrieves the embedding for the given text using the Azure OpenAI API.

    :param text: The text to retrieve the embedding for.
    :return: The embedding for the given text.
    """
    text = _normalize_text(text)
    embedding = _get_embedding(text)
    return embedding
