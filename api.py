from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from main import run_automation
from db import get_policyholder, list_policyholders_async, init_db
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_chroma import Chroma
from dotenv import load_dotenv
from logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

load_dotenv()

app = FastAPI(title="Insurance Renewal Automation API")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
import pathlib
static_dir = pathlib.Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# LLM for chatbot
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Vector Store for RAG
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)
vector_db = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)
retriever = vector_db.as_retriever(search_kwargs={"k": 3})

class PolicyholderResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    policy_id: str
    renewal_date: str
    days_remaining: int
    renewal_status: str
    preferred_channel: str
    history: List[str]

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("Application startup: Database initialized.")

@app.get("/")
async def serve_frontend():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Insurance Renewal Automation API is running"}

@app.get("/policyholders")
async def list_policyholders():
    phs = await list_policyholders_async()
    return {"policyholders": phs}

@app.get("/dashboard/stats")
async def get_stats():
    stats = {"EMAIL_SENT": 0, "WHATSAPP_SENT": 0, "VOICE_CALL_MADE": 0, "ESCALATED": 0, "PENDING": 0}
    phs = await list_policyholders_async()
    for ph in phs:
        status = ph.get("renewal_status", "PENDING")
        if status in stats:
            stats[status] += 1
        else:
            stats["PENDING"] += 1
    return stats

@app.post("/renew/{policyholder_id}")
async def trigger_renewal(policyholder_id: str):
    ph_data = await get_policyholder(policyholder_id)
    if not ph_data:
        raise HTTPException(status_code=404, detail=f"Policyholder {policyholder_id} not found")
    
    logger.info(f"API: Triggering renewal for {policyholder_id}")
    await run_automation(policyholder_id)
    
    updated_data = await get_policyholder(policyholder_id)
    return {"status": "success", "data": updated_data}

@app.get("/policyholder/{policyholder_id}", response_model=PolicyholderResponse)
async def get_status(policyholder_id: str):
    ph_data = await get_policyholder(policyholder_id)
    if not ph_data:
        raise HTTPException(status_code=404, detail=f"Policyholder {policyholder_id} not found")
    return ph_data

@app.post("/chat", response_model=ChatResponse)
async def chat_with_policy(request: ChatRequest):
    logger.info(f"API Chat: {request.message}")
    
    # Retrieve relevant context
    docs = await retriever.ainvoke(request.message)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    from agents.utils import get_prompt
    prompt_template = get_prompt("chatbot_rag.txt")
    system_prompt = prompt_template.format(context=context)
    
    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=request.message)
    ])
    return {"reply": response.content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
