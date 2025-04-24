from typing import Annotated, TypedDict, Sequence
from langgraph.graph.message import add_messages, BaseMessage

class AgentState(TypedDict):
    """Defines the state structure for the agent in the learning system."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    lesson: str