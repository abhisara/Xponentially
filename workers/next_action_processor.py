"""
Next Action Processor Worker
Suggests immediate next actionable step for short tasks.
"""
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from prompts.templates import get_processor_prompt


def next_action_processor_node(state: State) -> Command[Literal["executor"]]:
    """
    Process a short/planning task and suggest next action.

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
            name="next_action_processor"
        )
        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )

    task_id = task['id']
    task_classification = task_classifications.get(task_id, "short")

    # Check if this is an appropriate task type for next action processing
    appropriate_types = ['short', 'planning']
    if task_classification not in appropriate_types:
        warning_message = HumanMessage(
            content=f"Note: Task '{task['content']}' is classified as '{task_classification}', "
                    f"which is typically handled by research_processor. Processing anyway...",
            name="next_action_processor"
        )

    try:
        # Import model factory
        from config.model_factory import get_chat_model

        # Determine appropriate processor type based on classification
        processor_type = task_classification if task_classification in ['short', 'planning'] else 'short'

        # Generate processing prompt
        prompt = get_processor_prompt(processor_type, task)

        # Get next action from LLM
        model = get_chat_model()
        response = model.invoke(prompt)
        next_action = response.content if hasattr(response, 'content') else str(response)

        # Create result message
        result_message = HumanMessage(
            content=f"Next action for '{task['content']}':\n{next_action}",
            name="next_action_processor"
        )

        # Update processed results
        processed_results = state.get("processed_results", {})
        processed_results[task_id] = next_action

        # Note: In task-loop mode, the executor handles incrementing current_task_index
        # Only increment in legacy mode (when current_task_id is not set)
        update_dict = {
            "messages": [result_message],
            "processed_results": processed_results,
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
            content=f"Error processing task: {str(e)}",
            name="next_action_processor"
        )

        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )
