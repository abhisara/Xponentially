"""
LangGraph Workflow
Builds and compiles the task processing graph.
"""
from langgraph.graph import START, StateGraph

from helpers.state import State
from helpers.planner import planner_node
from helpers.executor import executor_node
from workers.todoist_fetcher import todoist_fetcher_node
from workers.task_classifier import task_classifier_node
from workers.research_processor import research_processor_node
from workers.next_action_processor import next_action_processor_node
from workers.learning_processor import learning_processor_node
from workers.planning_processor import planning_processor_node
from workers.markdown_writer import markdown_writer_node


def build_graph():
    """
    Build and compile the LangGraph workflow.

    Returns:
        Compiled graph ready for execution
    """
    # Create workflow
    workflow = StateGraph(State)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("todoist_fetcher", todoist_fetcher_node)
    workflow.add_node("task_classifier", task_classifier_node)
    workflow.add_node("research_processor", research_processor_node)
    workflow.add_node("next_action_processor", next_action_processor_node)
    workflow.add_node("learning_processor", learning_processor_node)
    workflow.add_node("planning_processor", planning_processor_node)
    workflow.add_node("markdown_writer", markdown_writer_node)

    # Set entry point
    workflow.add_edge(START, "planner")

    # Compile the workflow
    # Explicitly disable checkpointing since we don't need it for single-run workflows
    # Note: recursion_limit is set during invocation (in app.py), not during compilation
    return workflow.compile(checkpointer=None)


# Create singleton graph instance
graph = build_graph()
