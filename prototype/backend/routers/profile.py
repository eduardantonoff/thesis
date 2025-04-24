from fastapi import APIRouter, Request, HTTPException
from services.utilities import profile
from core.config import CONFIG, store
from typing import Dict, Any

router = APIRouter()

@router.get("/profile")
def get_profile(request: Request) -> Dict[str, Any]:
    """Endpoint to retrieve the user profile information.
    
    Returns:
        Dictionary containing the user profile data
    """
    try:
        user_profile = profile(config=CONFIG, store=store)
        return {"profile": user_profile}
    except Exception as e:
        # Handle errors gracefully
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )