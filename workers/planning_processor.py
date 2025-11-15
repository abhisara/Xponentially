"""
Planning Processor Worker
Processes planning tasks by analyzing progress, researching required steps, and comparing with completed work.
Uses web search to identify what steps are needed to reach the goal.
"""
from typing import Literal
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from helpers.observability import ExecutionTracker, create_enhanced_message_metadata
from prompts.templates import get_planning_processor_prompt


def planning_processor_node(state: State) -> Command[Literal["executor"]]:
    """
    Process a planning task with progress analysis and web search.

    This worker:
    - Extracts goal from task name
    - Analyzes steps taken so far from comments
    - Uses web search to identify required steps
    - Compares progress with required steps
    - Creates summary of done vs remaining

    Supports both task-loop mode (using current_task_id) and legacy mode (using current_task_index).

    Args:
        state: Current workflow state

    Returns:
        Command with updated state routing to executor
    """
    tasks = state.get("todoist_tasks", [])
    current_task_index = state.get("current_task_index", 0)
    current_task_id = state.get("current_task_id")
    task_classifications = state.get("task_classifications", {})

    # Get the task to process
    # Priority: use current_task_id if available (task-loop mode), otherwise use index
    task = None
    if current_task_id:
        # Task-loop mode: find task by ID
        task = next((t for t in tasks if t['id'] == current_task_id), None)
    elif current_task_index < len(tasks):
        # Legacy mode: use index
        task = tasks[current_task_index]

    if not task:
        error_message = HumanMessage(
            content="No task available to process",
            name="planning_processor"
        )
        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )

    task_id = task['id']
    task_classification = task_classifications.get(task_id, "planning")

    # Check if this is an appropriate task type for planning processing
    appropriate_types = ['planning']
    if task_classification not in appropriate_types:
        warning_message = HumanMessage(
            content=f"Note: Task '{task['content']}' is classified as '{task_classification}', "
                    f"which is typically handled by other processors. Processing as planning task anyway...",
            name="planning_processor"
        )

    try:
        # Start tracking execution
        exec_event = ExecutionTracker.start_node(
            node_name="planning_processor",
            task_id=task_id,
            task_index=current_task_index if not current_task_id else None,
            total_tasks=len(tasks)
        )

        # Import model factory
        from config.model_factory import get_tracked_chat_model

        # Get project name and comments
        project_id_to_name = state.get("project_id_to_name", {})
        project_name = project_id_to_name.get(task.get('project_id'), "Unknown Project")
        comments = task.get('comments', [])

        # Extract goal from task name (task content)
        goal = task['content']

        # Extract steps taken so far from comments
        steps_taken = []
        for comment in comments:
            content = comment.get('content', '').strip()
            if content:
                steps_taken.append(content)

        # Perform web search to identify required steps
        search_query = f"how to {goal} step by step guide checklist"
        search_results = perform_web_search(search_query)

        # Generate planning analysis prompt
        prompt = get_planning_processor_prompt(
            goal=goal,
            steps_taken=steps_taken,
            task_description=task.get('description', ''),
            project_name=project_name,
            search_results=search_results
        )

        # Get planning analysis from LLM with tracking
        model = get_tracked_chat_model(
            node_name="planning_processor",
            purpose="planning_analysis"
        )
        response = model.invoke(prompt)
        planning_analysis = response.content if hasattr(response, 'content') else str(response)

        # Finish tracking
        exec_event.finish()
        execution_timeline = state.get("execution_timeline", [])
        execution_timeline.append(exec_event.to_dict())

        # Create result message with metadata
        metadata = create_enhanced_message_metadata(
            node_name="planning_processor",
            task_id=task_id,
            task_index=current_task_index if not current_task_id else state.get("current_task_index"),
            total_tasks=len(tasks),
            execution_duration=exec_event.duration_seconds,
            task_type=task_classification
        )

        result_message = HumanMessage(
            content=f"Planning analysis for '{goal}':\n\n{planning_analysis}",
            name="planning_processor"
        )

        # Update processed results
        processed_results = state.get("processed_results", {})
        processed_results[task_id] = planning_analysis

        # Note: In task-loop mode, the executor handles incrementing current_task_index
        # Only increment in legacy mode (when current_task_id is not set)
        update_dict = {
            "messages": [result_message],
            "processed_results": processed_results,
            "execution_timeline": execution_timeline,
        }

        if not current_task_id:
            # Legacy mode: increment index
            update_dict["current_task_index"] = current_task_index + 1

        return Command(
            update=update_dict,
            goto="executor"
        )

    except Exception as e:
        error_message = HumanMessage(
            content=f"Error processing planning task: {str(e)}",
            name="planning_processor"
        )

        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )


def perform_web_search(query: str, max_results: int = 5) -> str:
    """
    Perform web search using DuckDuckGo search tool.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        Formatted string with search results
    """
    try:
        # Try DuckDuckGo search from langchain_community
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            
            search_tool = DuckDuckGoSearchRun()
            results = search_tool.run(f"{query}")
            
            # Format results
            if results:
                # Limit results length
                formatted_results = str(results)[:2000]  # Limit to 2000 chars
                return formatted_results
            else:
                return "No search results found."
        except ImportError:
            # Try alternative: duckduckgo-search package
            try:
                from duckduckgo_search import DDGS
                
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
                    if results:
                        formatted = "\n".join([
                            f"- {r.get('title', '')}: {r.get('body', '')[:200]}"
                            for r in results[:max_results]
                        ])
                        return formatted[:2000]
                    else:
                        return "No search results found."
            except ImportError:
                # Fallback: return message about installing search tools
                return "Web search not available. Install 'langchain-community' or 'duckduckgo-search' package for web search capabilities. Analysis will proceed without web search results."
            
    except Exception as e:
        return f"Error performing web search: {str(e)}. Analysis will proceed without web search results."

