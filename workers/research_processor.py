"""
Research Processor Worker
Analyzes research tasks and creates research plans.
Includes execution tracking and LLM call monitoring.
"""
from typing import Literal
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from helpers.observability import ExecutionTracker, create_enhanced_message_metadata
from prompts.templates import get_processor_prompt


def research_processor_node(state: State) -> Command[Literal["executor"]]:
    """
    Process a research task and create research plan.

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
            name="research_processor"
        )
        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )

    task_id = task['id']
    task_classification = task_classifications.get(task_id, "research")

    # Check if this is an appropriate task type for research processing
    appropriate_types = ['research', 'learning', 'abstract']
    if task_classification not in appropriate_types:
        warning_message = HumanMessage(
            content=f"Note: Task '{task['content']}' is classified as '{task_classification}', "
                    f"which is typically handled by next_action_processor. Processing anyway...",
            name="research_processor"
        )

    try:
        # Start tracking execution
        exec_event = ExecutionTracker.start_node(
            node_name="research_processor",
            task_id=task_id,
            task_index=current_task_index if not current_task_id else None,
            total_tasks=len(tasks)
        )

        # Import model factory
        from config.model_factory import get_tracked_chat_model

        # Determine appropriate processor type based on classification
        processor_type = task_classification if task_classification in ['research', 'learning', 'abstract', 'planning'] else 'research'

        # Generate processing prompt
        prompt = get_processor_prompt(processor_type, task)

        # Get research plan from LLM with tracking
        model = get_tracked_chat_model(
            node_name="research_processor",
            purpose=f"{processor_type}_processing"
        )
        response = model.invoke(prompt)
        research_plan = response.content if hasattr(response, 'content') else str(response)

        # Finish tracking
        exec_event.finish()
        execution_timeline = state.get("execution_timeline", [])
        execution_timeline.append(exec_event.to_dict())

        # Create result message with metadata
        metadata = create_enhanced_message_metadata(
            node_name="research_processor",
            task_id=task_id,
            task_index=current_task_index if not current_task_id else state.get("current_task_index"),
            total_tasks=len(tasks),
            execution_duration=exec_event.duration_seconds,
            task_type=task_classification
        )

        result_message = HumanMessage(
            content=f"Research plan for '{task['content']}':\n{research_plan}",
            name="research_processor"
        )
        # Note: LangChain messages don't natively support metadata, but we track it in state

        # Update processed results
        processed_results = state.get("processed_results", {})
        processed_results[task_id] = research_plan

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
            content=f"Error processing research task: {str(e)}",
            name="research_processor"
        )

        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )
