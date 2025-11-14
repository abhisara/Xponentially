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
    workflow.add_node("markdown_writer", markdown_writer_node)

    # Set entry point
    workflow.add_edge(START, "planner")

    # Compile and return
    return workflow.compile()


# Create singleton graph instance
graph = build_graph()


def run_workflow(user_query: str = "Process today's Todoist tasks"):
    """
    Run the task processing workflow.

    Args:
        user_query: User's request

    Returns:
        Final state after workflow completion
    """
    initial_state = {
        "user_query": user_query,
        "messages": [],
        "enabled_agents": [
            "todoist_fetcher",
            "task_classifier",
            "research_processor",
            "next_action_processor",
            "markdown_writer"
        ]
    }

    # Run graph
    result = graph.invoke(initial_state)
    return result
