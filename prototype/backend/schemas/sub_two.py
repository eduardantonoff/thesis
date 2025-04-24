from enum import Enum
import operator
from pydantic import BaseModel, Field
from typing import Annotated, TypedDict, Tuple, Union, List

class AssessmentSession(BaseModel):
    """Schema for initiating an assessment session."""
    input: str = Field(
        ..., 
        description="The topic or skill set to be assessed.",
        min_length=1
    )

class Eval(BaseModel):
    """Represents a single evaluation item within an assessment."""
    title: str = Field(
        ..., 
        description="A concise title for the evaluation.",
        min_length=3
    )
    description: str = Field(
        ..., 
        description="A description of the evaluation's content and purpose."
    )

class Evaluations(BaseModel):
    """A structured assessment plan composed of multiple evaluation items."""
    evals: List[Eval] = Field(
        ..., 
        description="An ordered list of evaluations, in sequential order."
    )

class EvalObject(BaseModel):
    """Represents a single evaluation object with content and criteria."""
    title: str = Field(
        ..., 
        description="Concise title of the evaluation object."
    )
    content: str = Field(
        ..., 
        description="Content of the evaluation object (question, multiple choice, code, etc.)."
    )
    evaluation_criteria: List[str] = Field(
        ..., 
        description="List of criteria that the evaluation should assess (e.g., knowledge of concepts, application skills)."
    )

class Report(BaseModel):
    """Represents the final report of an assessment session."""
    report: str = Field(
        ..., 
        description="A comprehensive summary of the assessment results and feedback.",
        min_length=50
    )

class ActionTypeE(str, Enum):
    """Enum for possible assessment action types."""
    EVALUATIONS = "evaluations"
    REPORT = "report"

class ActE(BaseModel):
    """Defines the next action to take in the assessment flow."""
    action: Union[Report, Evaluations] = Field(
        ..., 
        description="Choose an action: Report to finalize the assessment, or Evaluations to continue assessment."
    )
    action_type: ActionTypeE = Field(
        ...,
        description="Explicitly identifies whether this is a report or evaluations action."
    )

class EvalExecute(TypedDict):
    """Tracks the state of an assessment execution."""
    input: str
    evaluations: List[str]
    past_evals: Annotated[List[Tuple], operator.add]
    eo: Annotated[List[Tuple], operator.add]
    answer: Annotated[List[Tuple], operator.add]
    report: str