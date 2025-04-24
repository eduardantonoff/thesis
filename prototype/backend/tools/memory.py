import uuid
from typing import List, Dict
from langchain_core.tools import tool
from core.config import store, CONFIG

VALID_PROFILE_TYPES = frozenset({"name", "interests", "preferences", "goals"})

def _get_user_namespace(config=CONFIG) -> tuple:
    """Helper function to get user namespace for storage operations.
    
    Args:
        config: Application configuration
        
    Returns:
        Tuple containing the user namespace
        
    Raises:
        ValueError: If user ID is not found in config
    """
    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        raise ValueError("User ID not found in configuration.")
    return (user_id, "profile")

def _validate_profile_type(profile_type: str) -> None:
    """Validate that the profile type is allowed.
    
    Args:
        profile_type: Type of profile data
        
    Raises:
        ValueError: If profile type is invalid
    """
    if profile_type not in VALID_PROFILE_TYPES:
        raise ValueError(
            f"Invalid profile_type: '{profile_type}'. Valid types are: {', '.join(VALID_PROFILE_TYPES)}."
        )

@tool
def store_profile(content: str, profile_type: str, config=CONFIG, store=store) -> str:
    """Stores a user profile attribute in the database.
    
    Args:
        content: The value of the profile attribute to store
        profile_type: The category or type of the profile attribute.
                      Valid types include: "name", "interests", "preferences", "goals".
        config: Application configuration
        store: Data storage instance

    Returns:
        A confirmation message with stored content and its UUID
    
    Raises:
        ValueError: If an invalid profile type is provided or user ID not found
    """
    _validate_profile_type(profile_type)
    namespace = _get_user_namespace(config)
    memory_id = str(uuid.uuid4())
    
    store.put(
        namespace,
        key=memory_id,
        value={"memory": content, "type": profile_type},
        index=False
    )
    
    return f"Stored information: '{content}' | ID: {memory_id}"

@tool
def retrieve_profile(profile_type: str, config=CONFIG, store=store) -> List[Dict[str, str]]:
    """Retrieves user profile information of a specified type.

    Args:
        profile_type: The type of information to retrieve
        config: Application configuration
        store: Data storage instance

    Returns:
        A list of dictionaries, each with 'content' and 'id'

    Raises:
        ValueError: For invalid profile type or missing user ID
    """
    _validate_profile_type(profile_type)
    namespace = _get_user_namespace(config)
    results = store.search(namespace, filter={"type": profile_type})
    
    return [
        {"content": item.value.get("memory", ""), "id": item.key}
        for item in results
    ]

@tool
def delete_profile(key: str, config=CONFIG, store=store) -> str:
    """Deletes a specific user profile entry by its ID.

    Args:
        key: The unique ID of the profile entry to delete
        config: Application configuration
        store: Data storage instance

    Returns:
        A confirmation message if deleted or an error message if not found
    """
    try:
        namespace = _get_user_namespace(config)
        success = store.delete(namespace, key)
        
        if success:
            return f"Profile entry with ID {key} has been successfully deleted."
        else:
            return f"Error: No profile entry found with ID {key}."
    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except Exception as e:
        return f"An error occurred while deleting the profile entry: {str(e)}"