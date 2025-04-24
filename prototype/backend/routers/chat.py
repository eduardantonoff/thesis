from fastapi import APIRouter, HTTPException, Query
from typing import Dict
from core.config import CONFIG
from services.orchestration import main
from services.utilities import invoke_llm

router = APIRouter()

@router.get("/session-state")
async def get_session_state(config = CONFIG) -> Dict[str, str]:
    """Get the current session state from the graph.
    
    Returns:
        Dict containing the next state to be processed.
    """
    try:
        state = main.get_state(config)
        
        if not state.next:
            return {"next": ""}
            
        if isinstance(state.next, tuple) and len(state.next) == 1:
            return {"next": state.next[0]}
            
        return {"next": str(state.next)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session state: {str(e)}")

@router.get("/chat")
async def get_response(user_input: str = Query(..., description="User's message input")) -> Dict[str, str]:
    """Process user input and return AI response.
    
    Args:
        user_input: The user's message to process
        
    Returns:
        Dict containing the AI response
    """
    try:
        response, _ = invoke_llm(user_input, main)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat response: {str(e)}")