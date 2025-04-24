from core.config import CONFIG
from services.orchestration import main
from fastapi import APIRouter, Request
from typing import List, Dict, Any

router = APIRouter()

def _extract_items_from_state(state, key: str) -> List[Dict[str, str]]:
    """Helper function to extract items from state with error handling.
    
    Args:
        state: The state object from the graph
        key: The key to extract from state values
        
    Returns:
        List of dictionaries with item details
    """
    try:
        items = state.tasks[0].state.values[key]
        result = []
        
        for item in items:
            item_dict = {"title": item.title, "description": item.description}
            # Add learning_objective if it exists (only for plans)
            if hasattr(item, "learning_objective"):
                item_dict["learning_objective"] = item.learning_objective
            result.append(item_dict)
            
        return result
    except (IndexError, KeyError, AttributeError):
        return []

@router.get("/plan")
def get_user_plan(request: Request) -> Dict[str, Any]:
    """Endpoint to return the learning plan for the user.
    
    Returns:
        Dictionary containing the plan steps or an empty list if no plan exists
    """
    try:
        state = main.get_state(config=CONFIG, subgraphs=True)
        plan_items = _extract_items_from_state(state, 'plan')
        return {"plan": plan_items}
    except Exception as ex:
        return {"error": str(ex), "plan": []}

@router.get("/assessment")
def get_user_assessment(request: Request) -> Dict[str, Any]:
    """Endpoint to return the assessment evaluations for the user.
    
    Returns:
        Dictionary containing the evaluation items or an empty list if none exist
    """
    try:
        state = main.get_state(config=CONFIG, subgraphs=True)
        evaluation_items = _extract_items_from_state(state, 'evaluations')
        return {"plan": evaluation_items}
    except Exception as ex:
        return {"error": str(ex), "plan": []}