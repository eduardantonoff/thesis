import os
import re
import json
from typing import List, Dict, Any, Optional, Union
from langchain_core.tools import tool
from core.config import GRAPH_PATH, graph_data

ALLOWED_STATUSES = frozenset({"mastery", "unlearned", "awareness"})
CONCEPT_ID_PATTERN = re.compile(r'^[A-Z]\.\d+$')

def _validate_data(data: Dict[str, Any]) -> Optional[str]:
    """Validates the graph data structure.
    
    Args:
        data: Graph data dictionary
        
    Returns:
        Error message if invalid, None if valid
    """
    if data is None:
        return "Error: 'data' dictionary not provided."
    if "concepts" not in data:
        return "Error: 'concepts' key not found in the data dictionary."
    return None

def _load_graph_data(path: str) -> Union[Dict[str, Any], str]:
    """Loads graph data from file with error handling.
    
    Args:
        path: Path to the graph JSON file
        
    Returns:
        Graph data dictionary or error message string
    """
    if not os.path.exists(path):
        return f"Error: File '{path}' does not exist."
    
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as jde:
        return f"Error reading JSON from '{path}': {jde}"
    except Exception as e:
        return f"Error opening '{path}': {e}"

@tool
def retrieve_sections(section_letter: str, data: dict = graph_data) -> Union[List[Dict[str, str]], str]:
    """Retrieves a list of concepts belonging to a specific section.

    Args:
        section_letter: The letter of the section to retrieve concepts from (e.g., "A", "B").
        data: The dictionary containing concept data.

    Returns:
        A list of dictionaries, where each dictionary represents a concept and contains:
            - "id": The unique ID of the concept.
            - "label": The name or label of the concept.  
        Returns an empty list if no concepts are found for the given section.
        Returns an error message if input is invalid.
    """
    error = _validate_data(data)
    if error:
        return error
        
    if not isinstance(section_letter, str) or not section_letter.isalpha() or len(section_letter) != 1:
        return "Error: Invalid section letter. Must be a single alphabet character."
    
    results = [
        {"id": concept_id, "label": concept_info["label"]}
        for concept_id, concept_info in data["concepts"].items()
        if concept_info.get("section") == section_letter.upper()
    ]
    
    return results

@tool
def retrieve_concept(concept_id: str, data: dict = graph_data) -> Union[Dict[str, Any], str, None]:
    """Retrieves a concept by its unique ID.

    Args:
        concept_id: The ID of the concept to retrieve.
        data: The dictionary containing concept data.

    Returns:
        A dictionary containing the concept's information if found, otherwise returns None.  
        The concept dictionary, if found, will typically contain keys like "label", "section", and other relevant details.
        Returns an error message if input is invalid.
    """
    error = _validate_data(data)
    if error:
        return error
        
    if not isinstance(concept_id, str):
        return "Error: Invalid concept ID. Must be a string."
    
    return data["concepts"].get(concept_id)

@tool
def update_concept_status(concept_id: str, new_status: str, path: str = GRAPH_PATH) -> str:
    """Updates a concept's status in a JSON file and saves the changes.

    Args:
        concept_id: The ID of the concept to update. Must follow the format 'Letter.Number' (e.g., 'A.1').
        new_status: The new status for the concept. Must be one of "mastery", "unlearned", or "awareness".
        path: Path to the graph JSON file.

    Returns:
        A message indicating success or failure, including details of any errors.
    """
    if not isinstance(concept_id, str):
        return "Error: Invalid concept ID type. Must be a string."
        
    if not CONCEPT_ID_PATTERN.match(concept_id):
        return ("Error: Invalid concept ID format. "
                "The correct format is a single uppercase letter followed by a dot and a number (e.g., 'A.1').")
                
    if not isinstance(new_status, str):
        return "Error: Invalid status type. Must be a string."

    if new_status not in ALLOWED_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_STATUSES))
        return f"Error: Invalid status '{new_status}'. Allowed statuses are: {allowed}."
    
    data = _load_graph_data(path)
    if isinstance(data, str):
        return data
        
    if "concepts" not in data:
        return "Error: 'concepts' key not found in the JSON data."
        
    if concept_id in data["concepts"]:
        current_status = data["concepts"][concept_id].get("status", "undefined")
        
        if current_status == new_status:
            return f"No update needed: Concept '{concept_id}' is already set to '{new_status}'."
            
        data["concepts"][concept_id]["status"] = new_status
        
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
            return (f"Success: Status of concept '{concept_id}' updated from "
                    f"'{current_status}' to '{new_status}'.")
        except Exception as e:
            return f"Error saving changes to '{path}': {e}"
    else:
        return f"Error: Concept with ID '{concept_id}' not found."
    
@tool
def get_prerequisites(concept_id: str, path: str = GRAPH_PATH) -> str:
    """Retrieves all prerequisites for a given concept ID, including their IDs and labels.

    Args:
        concept_id: The ID of the concept whose prerequisites are to be retrieved.
        path: Path to the graph JSON file.

    Returns:
        A formatted string of prerequisites or an error message.
    """
    if not re.match(CONCEPT_ID_PATTERN, concept_id):
        return (f"Error: Invalid concept ID format '{concept_id}'. "
                "The correct format should be a letter followed by a dot and number, e.g., 'A.1'.")
    
    data = _load_graph_data(path)
    if isinstance(data, str):
        return data
        
    if "concepts" not in data:
        return "Error: 'concepts' key not found in the JSON data."
        
    if concept_id not in data["concepts"]:
        return f"Error: Concept with ID '{concept_id}' not found."
    
    prerequisites_ids = data["concepts"][concept_id].get("prerequisites", [])
    
    if not prerequisites_ids:
        return f"Concept '{concept_id}' has no prerequisites."
    
    prerequisites = []
    missing_prereqs = []
    
    for pid in prerequisites_ids:
        prereq = data["concepts"].get(pid)
        if prereq:
            prerequisites.append({"ID": pid, "Label": prereq.get("label", "N/A")})
        else:
            missing_prereqs.append(pid)
    
    output_lines = [f"Prerequisites for Concept '{concept_id}':"]
    
    for prereq in prerequisites:
        output_lines.append(f" - {prereq['ID']}: {prereq['Label']}")
    
    if missing_prereqs:
        output_lines.append("\nWarning: The following prerequisite IDs were not found in the data:")
        for pid in missing_prereqs:
            output_lines.append(f" - {pid}")
    
    return "\n".join(output_lines)