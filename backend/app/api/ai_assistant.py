from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.services.ai_service import chat_with_ai, generate_daily_insights, analyze_health_correlation
from app.config import get_settings

router = APIRouter(prefix="/ai", tags=["AI Assistant"])
settings = get_settings()


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    message: str
    role: str = "assistant"


class CorrelationRequest(BaseModel):
    metric1: str
    metric2: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set ANTHROPIC_API_KEY."
        )

    try:
        history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
        response = await chat_with_ai(
            user_message=request.message,
            conversation_history=history,
            user=current_user,
            db=db,
        )
        return ChatResponse(message=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.get("/insights")
async def get_daily_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured.")

    try:
        insights = await generate_daily_insights(current_user, db)
        return {"insights": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/correlate")
async def correlate_metrics(
    request: CorrelationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured.")

    try:
        analysis = await analyze_health_correlation(
            request.metric1, request.metric2, current_user, db
        )
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.get("/suggested-questions")
def get_suggested_questions(current_user: User = Depends(get_current_user)):
    """Return contextual suggested questions for the chat interface."""
    return {
        "questions": [
            "Why was my sleep bad last night?",
            "How has my HRV changed over the last month?",
            "What's the relationship between my diet and my recovery score?",
            "Am I getting enough protein for my workout goals?",
            "When should I work out based on my recovery data?",
            "What do my lab results say about my cardiovascular health?",
            "How does my caffeine/alcohol intake affect my sleep quality?",
            "What's my biggest health risk factor right now?",
            "How is my hydration affecting my performance?",
            "Am I overtraining based on my strain and recovery data?",
            "What nutrients am I deficient in based on my diet and blood work?",
            "How does my sleep compare to last month?",
        ]
    }
