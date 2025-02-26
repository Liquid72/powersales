import asyncio
from fastapi import FastAPI
from src.routes import llm, debug
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from src.utility.transaction import check_transaction_jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup")
    asyncio.create_task(check_transaction_jobs())
    yield
    print("Shutdown")


app = FastAPI()


app.include_router(llm.router)
app.include_router(debug.router, tags=["debug"])
