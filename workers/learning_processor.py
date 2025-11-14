"""
Learning Processor Worker
Specialized worker for educational and learning tasks with context awareness.
Tracks progress, resources, and next steps for continuous learning.
"""
from typing import Literal
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from helpers.observability import ExecutionTracker, create_enhanced_message_metadata
from helpers.context_loader import load_context_for_task, format_context_for_prompt
from prompts.templates import get_processor_prompt


def learning_processor_node(state: State) -> Command[Literal["executor"]]:
    """
    Process a learning/educational task with context awareness.

    This worker:
    - Loads learning context (if available) for continuity
    - Creates structured learning plans
    - Tracks progress and resources
    - Suggests next steps

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
            name="learning_processor"
        )
        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )

    task_id = task['id']
    task_classification = task_classifications.get(task_id, "learning")

    # Check if this is an appropriate task type for learning processing
    appropriate_types = ['learning', 'research', 'abstract']
    if task_classification not in appropriate_types:
        warning_message = HumanMessage(
            content=f"Note: Task '{task['content']}' is classified as '{task_classification}', "
                    f"which is typically handled by next_action_processor. Processing as learning task anyway...",
            name="learning_processor"
        )

    try:
        # Start tracking execution
        exec_event = ExecutionTracker.start_node(
            node_name="learning_processor",
            task_id=task_id,
            task_index=current_task_index if not current_task_id else None,
            total_tasks=len(tasks)
        )

        # Load context file if available
        context_path, context_content = load_context_for_task(task)

        context_info = ""
        task_context_files = state.get("task_context_files", {})

        if context_path and context_content:
            # Track which context file was used
            task_context_files[task_id] = context_path
            context_info = format_context_for_prompt(context_content, "Learning")

        # Import model factory
        from config.model_factory import get_tracked_chat_model

        # Generate learning-specific processing prompt
        prompt = get_processor_prompt(
            processor_type="learning",
            task=task,
            context=context_info if context_info else None
        )

        # Get learning plan from LLM with tracking
        model = get_tracked_chat_model(
            node_name="learning_processor",
            purpose="learning_task_processing"
        )
        response = model.invoke(prompt)
        learning_output = response.content if hasattr(response, 'content') else str(response)

        # Finish tracking
        exec_event.finish()
        execution_timeline = state.get("execution_timeline", [])
        execution_timeline.append(exec_event.to_dict())

        # Create result message with metadata
        metadata = create_enhanced_message_metadata(
            node_name="learning_processor",
            task_id=task_id,
            task_index=current_task_index if not current_task_id else state.get("current_task_index"),
            total_tasks=len(tasks),
            execution_duration=exec_event.duration_seconds,
            task_type=task_classification
        )

        # Add context info to result message if context was used
        context_note = ""
        if context_path:
            import os
            context_filename = os.path.basename(context_path)
            context_note = f"\n\n*(Used context from {context_filename})*"

        result_message = HumanMessage(
            content=f"Learning plan for '{task['content']}':\n{learning_output}{context_note}",
            name="learning_processor"
        )

        # Update processed results
        processed_results = state.get("processed_results", {})
        processed_results[task_id] = learning_output

        # Note: In task-loop mode, the executor handles incrementing current_task_index
        # Only increment in legacy mode (when current_task_id is not set)
        update_dict = {
            "messages": [result_message],
            "processed_results": processed_results,
            "execution_timeline": execution_timeline,
            "task_context_files": task_context_files,  # Track context usage
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
            content=f"Error processing learning task: {str(e)}",
            name="learning_processor"
        )

        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )
