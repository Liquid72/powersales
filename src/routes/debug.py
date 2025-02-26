import os
from fastapi import APIRouter
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

from src.utility.rag import get_document
load_dotenv()
router = APIRouter()


llm_model = AzureChatOpenAI(
    api_key=os.getenv("API_KEY"),
    azure_endpoint=os.getenv("ENDPOINT"),
    api_version=os.getenv("VERSION"),
    azure_deployment=os.getenv("DEPLOYMENT_NAME"),
    max_tokens=8096
)


@router.get("/test_rag")
async def test_rag(query: str):
    docs = get_document(query)
    return docs
