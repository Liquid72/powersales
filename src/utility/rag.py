import os
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()

azure_endpoint: str = os.getenv("ENDPOINT_EMBEDDING")
azure_openai_api_key: str = os.getenv("API_KEY_EMBEDDING")
azure_openai_api_version: str = os.getenv("VERSION_EMBEDDING")
azure_deployment: str = os.getenv("DEPLOYMENT_NAME_EMBEDDING")

vector_store_address: str = os.getenv("AZURE_SEARCH_ENDPOINT")
vector_store_password: str = os.getenv("AZURE_SEARCH_KEY")

embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
    azure_deployment=azure_deployment,
    openai_api_version=azure_openai_api_version,
    azure_endpoint=azure_endpoint,
    api_key=azure_openai_api_key,
)

index_name: str = "catalog"
vector_store: AzureSearch = AzureSearch(
    azure_search_endpoint=vector_store_address,
    azure_search_key=vector_store_password,
    index_name=index_name,
    embedding_function=embeddings.embed_query,
)


def get_document(query: str, k: int = 5):
    """
    Get the document with the highest similarity to the query
    """
    
    return vector_store.similarity_search_with_relevance_scores(query, k=k, score_threshold=0.65)
