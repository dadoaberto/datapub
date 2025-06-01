from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import Optional

app = FastAPI()

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5

@app.post("/query")
async def query_documents(request: QueryRequest):
    return {
        "message": "API funcionando",
        "question": request.question,
        "top_k": request.top_k
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
