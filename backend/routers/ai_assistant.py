"""
AI Assistant Router 

Shriram tasks:
1. Load user preferences from DB on first query
2. Use Langchain for NLP and query interpretation
3. Extract: cuisine type, price range, dietary restrictions, occasion, ambiance
4. Query restaurant DB with filters
5. Rank results based on relevance + user preferences
6. Use Tavily web search for additional context
7. Support multi-turn conversations

Required env vars:
- OPENAI_API_KEY
- TAVILY_API_KEY
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    AI chatbot endpoint.
    
    Input:
        {
            "message": "user natural language query",
            "conversation_history": [{"role": "user|assistant", "content": "..."}]
        }
    
    Output:
        {
            "response": "AI-generated response text",
            "recommendations": [
                {
                    "id": 1,
                    "name": "Restaurant Name",
                    "rating": 4.5,
                    "price_tier": "$$",
                    "cuisine_type": "Italian",
                    "reason": "Matches your Italian preference"
                }
            ]
        }
    
    TODO: Replace this stub with Langchain + Tavily implementation.
    Steps:
        1. Load user prefs: db.query(models.UserPreferences).filter(...).first()
        2. Initialize Langchain LLM (ChatOpenAI) with system prompt containing prefs
        3. Parse user message to extract filters
        4. Query restaurants from DB with extracted filters
        5. Use Tavily to search for current hours/events if needed
        6. Rank and return results with conversational response
    """
    # Stub response: replace with real implementation
    return schemas.ChatResponse(
        response="AI Assistant is not yet implemented. Complete this feature.",
        recommendations=[],
    )
