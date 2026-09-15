from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.graph.graph import casepilot_graph


app = FastAPI(
    title="CasePilot API",
    description="AI-powered customer support resolution API",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
# Allows the React frontend running on localhost:5173
# to communicate with this backend.
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------

class ChatRequest(BaseModel):
    customer_message: str = Field(
        ...,
        min_length=1,
        description="Message sent by the customer",
    )


class ChatResponse(BaseModel):
    message: str
    transaction_amount: float | None = None
    authorization: str | None = None
    requires_human: bool = False
    status: str


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "casepilot-api",
    }


# ---------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    result = casepilot_graph.invoke(
        {
            "customer_message": request.customer_message,
        }
    )

    return ChatResponse(
        message=result.get(
            "investigation",
            "I couldn't investigate the case.",
        ),
        transaction_amount=result.get("transaction_amount"),
        authorization=result.get("authorization"),
        requires_human=result.get("requires_human", False),
        status=result.get("status", "UNKNOWN"),
    )