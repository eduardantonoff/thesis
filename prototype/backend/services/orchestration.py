import os
import json
from typing import Dict, Any, List

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, trim_messages
from langchain.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from langgraph.graph import START, END, StateGraph, MessagesState

from services.utilities import prepare_messages, profile, knowledge_state
from prompts.sub_two import mapper_, assessor_, remaper_
from prompts.sub_one import replaner_, planner_, learner_
from core.config import llm, checkpointer
from schemas.state import AgentState
from schemas.sub_one import PlanExecute, Plan, LearningObject, Conclusion, Act, LearningSession
from schemas.sub_two import EvalExecute, Evaluations, EvalObject, Report, ActE, AssessmentSession
from tools.memory import store_memory, retrieve_memory, delete_memory
from tools.retreival import retrieve_sections, retrieve_node, update_status, retrieve_prerequisites

load_dotenv(dotenv_path='.env', override=True)

langsmith_api = os.getenv("LANGSMITH_API_KEY")
if langsmith_api:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "Agent Two"

planner = ChatPromptTemplate.from_messages([
    ("system", planner_), 
    ("placeholder", "{messages}")
]) | llm.with_structured_output(Plan)

object = ChatPromptTemplate.from_messages([
    ("system", learner_), 
    ("placeholder", "{messages}")
]) | llm.with_structured_output(LearningObject)

replanner = ChatPromptTemplate.from_template(replaner_) | llm.with_structured_output(Act)

mapper = ChatPromptTemplate.from_messages([
    ("system", mapper_),
    ("placeholder", "{messages}")
]) | llm.with_structured_output(Evaluations)

assessment = ChatPromptTemplate.from_messages([
    ("system", assessor_), 
    ("placeholder", "{messages}")
]) | llm.with_structured_output(EvalObject)

remapper = ChatPromptTemplate.from_template(remaper_) | llm.with_structured_output(ActE)

def execute_step(state: PlanExecute) -> Dict[str, Any]:
    """Execute a learning step from the plan.
    
    Args:
        state: Current execution state
        
    Returns:
        Updated state with learning object
    """
    plan = state["plan"]
    current_step = plan[0]
    plan_str = "\n".join(
        f"{i+1}. {step.title}\nDescription: {step.description}\nLearning Objective: {step.learning_objective}\n"
        for i, step in enumerate(plan))
    
    user_info = profile()

    personalize = f"""Content is presented to: {user_info}. 
                      Who's current knowledge state is: {knowledge_state()}
                      """

    if state["past_steps"]:
        previous_steps_str = ". ".join([f'{i+1}. {desc}' for i, desc in enumerate(state["past_steps"])])
        prompt = f"""You are a Learning Experience Designer.
                     Given this plan:\n{plan_str}\n
                     And, having already covered introduction: {previous_steps_str}\n
                     Your task is to teach: {current_step}."""
    else:
        prompt = f"""You are a Learning Experience Designer.
                     Given this learning plan:\n{plan_str}\n
                     Your task is to provide an introduction / a warm up: {current_step}, anticipating the main lesson."""

    result = object.invoke({"messages": [("user", prompt + personalize)]})
    return {"past_steps": [current_step], "lo": result}

def plan_step(state: PlanExecute) -> Dict[str, List]:
    """Create a learning plan based on user input.
    
    Args:
        state: Current execution state
        
    Returns:
        Updated state with plan steps
    """
    plan = planner.invoke({"messages": [("user", state["input"])]})
    return {"plan": plan.steps}

def replan_step(state: PlanExecute) -> Dict[str, Any]:
    """Replan learning steps or create conclusion.
    
    Args:
        state: Current execution state
        
    Returns:
        Updated state with new plan or conclusion
    """
    output = replanner.invoke(state)
    prefix = "Learning content that was introduced to the user."
    return {"conclusion": prefix + output.action.conclusion} if isinstance(output.action, Conclusion) else {"plan": output.action.steps}

def disclose(state: PlanExecute) -> Command:
    """Determine if interruption is needed.
    
    Args:
        state: Current execution state
        
    Returns:
        Command to replan or end
    """
    return Command(goto="replan") if interrupt({"llm_output": state["lo"]}) else Command(goto=END)

def should_end(state: PlanExecute) -> str:
    """Determine if learning session should end.
    
    Args:
        state: Current execution state
        
    Returns:
        Next node or END
    """
    return END if state.get("conclusion") else "learning_object"

learningflow = StateGraph(PlanExecute)

learningflow.add_node("planner", plan_step)
learningflow.add_node("learning_object", execute_step)
learningflow.add_node("replan", replan_step)
learningflow.add_node("disclosure", disclose)
learningflow.add_edge(START, "planner")
learningflow.add_edge("planner", "learning_object")
learningflow.add_edge("learning_object", "disclosure")
learningflow.add_edge("disclosure", "replan")
learningflow.add_conditional_edges("replan", should_end, ["learning_object", END])

learningapp = learningflow.compile()

def execute_eval(state: EvalExecute) -> Dict[str, Any]:
    """Execute an evaluation step.
    
    Args:
        state: Current evaluation state
        
    Returns:
        Updated state with evaluation object
    """
    evaluations = state["evaluations"]
    current_eval = evaluations[0]
    eval_str = "\n".join(f"{i+1}. {eval}" for i, eval in enumerate(evaluations, start=1))
    prompt = f"""Given this learning session content {state['input']}\n\n, and evaluation plan:\n{eval_str}
                 You are tasked with executing evaluation {1}: {current_eval}.
                 Questions / tasks must directly align with the learning session content."""
    result = assessment.invoke({"messages": [("user", prompt)]})
    return {"past_evals": [current_eval], "eo": [result]}

def plan_eval(state: EvalExecute) -> Dict[str, List]:
    """Create an evaluation plan.
    
    Args:
        state: Current evaluation state
        
    Returns:
        Updated state with evaluation plan
    """
    evaluations = mapper.invoke({"messages": [("user", state["input"])]})
    return {"evaluations": evaluations.evals}

def remap_eval(state: EvalExecute) -> Dict[str, Any]:
    """Process evaluation results and create report or new evaluations.
    
    Args:
        state: Current evaluation state
        
    Returns:
        Updated state with report or new evaluations
    """
    output = remapper.invoke(state)
    formatted_list = []
    for i, eval_obj in enumerate(state['eo'], 1):
        content = eval_obj.content.strip()
        formatted_list.append(f"{i}. {content}")
    prompt = f"Questions: {str(formatted_list)} | Answers: {str(state['answer'])}"
    return {"report": output.action.report + prompt} if isinstance(output.action, Report) else {"evaluations": output.action.evals}

def assess(state: EvalExecute) -> Dict[str, List]:
    """Get user answer for assessment.
    
    Args:
        state: Current evaluation state
        
    Returns:
        Updated state with user answer
    """
    answer = interrupt("Please provide your answer: ")
    return {"answer": [answer]}

def should_end_eval(state: EvalExecute) -> str:
    """Determine if evaluation session should end.
    
    Args:
        state: Current evaluation state
        
    Returns:
        Next node or END
    """
    return END if state.get("report") else "evaluation_object"

evaluationflow = StateGraph(EvalExecute)

evaluationflow.add_node("mapper", plan_eval)
evaluationflow.add_node("evaluation_object", execute_eval)
evaluationflow.add_node("remap", remap_eval)
evaluationflow.add_node("assessment", assess)

evaluationflow.add_edge(START, "mapper")
evaluationflow.add_edge("mapper", "evaluation_object")
evaluationflow.add_edge("evaluation_object", "assessment")
evaluationflow.add_edge("assessment", "remap")

evaluationflow.add_conditional_edges("remap", should_end_eval, ["evaluation_object", END])

assessmentapp = evaluationflow.compile()

tools = [
    store_memory, 
    retrieve_memory, 
    delete_memory, 
    retrieve_sections, 
    retrieve_node, 
    update_status, 
    retrieve_prerequisites
]
 
tool_node = ToolNode(tools)

model = llm.bind_tools(tools + [LearningSession] + [AssessmentSession])

tools_by_name = {tool.name: tool for tool in tools}

def call_model(state: AgentState, config: RunnableConfig) -> Dict[str, List]:
    """Process user messages and generate model response.
    
    Args:
        state: Current agent state
        config: Runtime configuration
        
    Returns:
        Updated state with model response
    """
    messages = trim_messages(
        state['messages'], 
        strategy="last", 
        token_counter=len, 
        max_tokens=15, 
        start_on="human", 
        end_on=("human", "tool"), 
        include_system=True
    )
    system_prompt = SystemMessage(prepare_messages({"messages": []})[0]["content"])
    response = model.invoke([system_prompt] + messages, config)
    return {"messages": [response]}

def learning_loop(state: AgentState) -> Dict[str, Any]:
    """Execute the learning session loop.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with learning response
    """
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    topic = state["messages"][-1]
    response = learningapp.invoke({
        "input": json.loads(topic.additional_kwargs['tool_calls'][0]['function']['arguments'])["input"]
    })
    tool_message = [{"tool_call_id": tool_call_id, "type": "tool", "content": response}]
    return {"messages": tool_message, "lesson": response}

def assessment_loop(state: AgentState) -> Dict[str, List]:
    """Execute the assessment session loop.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with assessment response
    """
    tool_call_id = state["messages"][-1].tool_calls[0]["id"]
    topic = state["lesson"]['lo'].content
    response = assessmentapp.invoke({"input": str(topic)})
    tool_message = [{"tool_call_id": tool_call_id, "type": "tool", "content": response}]
    return {"messages": tool_message}

def should_continue(state: AgentState) -> str:
    """Determine next node based on message content.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node or END
    """
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    elif last_message.tool_calls[0]["name"] == "LearningSession":
        return "learning session"
    elif last_message.tool_calls[0]["name"] == "AssessmentSession":
        return "evaluation session"
    else:
        return "tools"

mainflow = StateGraph(MessagesState)

mainflow.add_node("agent", call_model)
mainflow.add_node("tools", tool_node)
mainflow.add_node("learning session", learning_loop)
mainflow.add_node("evaluation session", assessment_loop)

mainflow.add_edge(START, "agent")
mainflow.add_conditional_edges("agent", should_continue)
mainflow.add_edge("tools", "agent")
mainflow.add_edge("learning session", "agent")
mainflow.add_edge("evaluation session", "agent")

main = mainflow.compile(checkpointer=checkpointer)