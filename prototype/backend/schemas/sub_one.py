from enum import Enum
import operator
from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, Tuple, Union, List

class LearningSession(BaseModel):
    """Schema for initiating a learning session with a topic."""
    input: str = Field(
        ..., 
        description="A topic for the learning session based on knowledge graph data.",
        min_length=1
    )

class Step(BaseModel):
    """Represents a single learning step within a plan."""
    title: str = Field(
        ..., 
        description="A concise title for the step.",
        min_length=3
    )
    description: str = Field(
        ..., 
        description="A detailed description of what this step entails."
    )
    learning_objective: str = Field(
        ..., 
        description="The specific learning objective this step addresses."
    )

class Plan(BaseModel):
    """A structured learning plan composed of multiple steps."""
    steps: List[Step] = Field(
        ..., 
        description="An ordered list of learning steps in sequential order."
    )

class LearningObject(BaseModel):
    """Represents a single learning object/content item."""
    title: str = Field(
        ..., 
        description="A concise title for the learning object."
    )
    content: str = Field(
        ..., 
        description="The learning content material."
    )

class Conclusion(BaseModel):
    """Represents the final summary of a learning session."""
    conclusion: str = Field(
        ..., 
        description="A brief overview of the lesson's content (approximately 50 words).",
        max_length=300
    )

class ActionType(str, Enum):
    """Enum for possible action types."""
    PLAN = "plan"
    CONCLUSION = "conclusion"

class Act(BaseModel):
    """Defines the next action to take in the learning flow."""
    action: Union[Conclusion, Plan] = Field(
        ..., 
        description="Choose an action: Conclusion to finalize the session, or Plan to define more steps."
    )
    action_type: ActionType = Field(
        ...,
        description="Explicitly identifies whether this is a conclusion or plan action."
    )

class PlanExecute(TypedDict):
    """Tracks the state of a learning plan execution."""
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    lo: str  # learning objective
    conclusion: str