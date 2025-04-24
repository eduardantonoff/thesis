import os
import json
from typing import Dict, List, Any, Tuple
from langgraph.types import Command
from core.config import CONFIG, store, GRAPH_PATH
from prompts.base import persona, knowledge_space, protocol, memory, guidelines

def knowledge_state(path: str = GRAPH_PATH) -> str:
    """Reads the knowledge graph and returns a formatted string of concepts with their status.
    
    Args:
        path: Path to the knowledge graph JSON file
        
    Returns:
        Formatted string containing concepts and their status
    """
    if not os.path.exists(path):
        return f"Error: File '{path}' does not exist."

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as jde:
        return f"Error reading JSON from '{path}': {jde}"
    except Exception as e:
        return f"Error opening '{path}': {e}"

    if "concepts" not in data:
        return "Error: 'concepts' key not found in the JSON data."

    concepts_with_status = [
        {
            "ID": cid,
            "Label": details.get("label", "N/A"),
            "Status": details.get("status", "N/A")
        }
        for cid, details in data["concepts"].items()
        if details.get("status")
    ]

    if not concepts_with_status:
        return "No concepts with a non-empty status found."
    
    concepts_with_status.sort(key=lambda x: x["ID"])
    formatted_lines = [
        f"Concept ID: {c['ID']} Label: {c['Label'].title()} status is {c['Status']}" 
        for c in concepts_with_status
    ]
    
    return "\n".join(formatted_lines)

def prepare_messages(state: Dict[str, Any], config: Dict = CONFIG, store: Any = store) -> List[Dict[str, str]]:
    """Prepare system and user messages for LLM interaction.
    
    Args:
        state: Current conversation state
        config: Application configuration
        store: Data storage instance
        
    Returns:
        List of message dictionaries
    """
    user_id = config["configurable"]["user_id"]
    namespace = (user_id, "profile")
    profile_types = {
        "name": "Name", 
        "interests": "Interests", 
        "preferences": "Preferences", 
        "goals": "Goals"
    }

    # Build profile lines efficiently
    profile_lines = []
    for p_type, label in profile_types.items():
        memories = store.search(namespace, filter={'type': p_type}, limit=5)
        memory_text = ' '.join(m.value['memory'] for m in memories)
        profile_lines.append(f"* {label}: {memory_text}")
    
    user_profile = "\n".join(profile_lines)
    
    # Construct system message with all context
    system_message = {
        "role": "system",
        "content": (
            f"{persona}\n\n"
            f"**User's Profile:**\n{user_profile}\n\n"
            f"**User's Current Knowledge State:**\n{knowledge_state()}\n\n"
            f"{knowledge_space}\n\n"
            f"**Interaction Protocol:**\n{protocol}\n\n"
            f"**Profile Management Instructions:**\n{memory}\n\n"
            f"**Guidelines:**\n{guidelines}\n\n"
        )
    }
    
    return [system_message] + state["messages"]

def profile(config: Dict = CONFIG, store: Any = store) -> str:
    """Get formatted user profile information.
    
    Args:
        config: Application configuration
        store: Data storage instance
        
    Returns:
        Formatted user profile as string
    """
    user_id = config["configurable"]["user_id"]
    namespace = (user_id, "profile")
    profile_types = {
        "name": "Name", 
        "goals": "Goals", 
        "interests": "Interests", 
        "preferences": "Preferences"
    }

    profile_lines = []
    for p_type, label in profile_types.items():
        memories = store.search(namespace, filter={'type': p_type}, limit=5)
        memory_text = ' '.join(m.value['memory'] for m in memories)
        profile_lines.append(f"{label}: {memory_text}")
    
    return "\n".join(profile_lines)

def invoke_llm(input_string: str, main: Any, config: Dict = CONFIG) -> Tuple[str, Any]:
    """Invoke the LLM with user input and handle different states.
    
    Args:
        input_string: User input text
        main: Main graph instance
        config: Application configuration
        
    Returns:
        Tuple of (response content, full response)
    """
    state = main.get_state(config)
    payload = {"messages": [{"role": "user", "content": input_string}]}

    if state.next in [('learning session',), ('evaluation session',)]:
        command = Command(resume=input_string)
        response = main.invoke(command, config=config, subgraphs=True)
    elif not state.next:
        response = main.invoke(payload, config=config, subgraphs=True)
    else:
        raise ValueError(f"Unexpected state.next value: {state.next}")

    response_content = "No valid content found in the response."
    
    response_data = response[1] if len(response) > 1 and isinstance(response[1], dict) else {}

    if 'messages' in response_data and isinstance(response_data['messages'], list) and response_data['messages']:
        last_message = response_data['messages'][-1]
        response_content = getattr(last_message, 'content', response_content)
    elif 'lo' in response_data:
        response_content = getattr(response_data['lo'], 'content', response_content)
    elif 'eo' in response_data:
        response_content = getattr(response_data['eo'][-1], 'content', response_content)

    return response_content, response