"""
Task Classifier Worker
Classifies tasks into types: research, planning, short, learning, or abstract.
"""
import json
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from prompts.templates import get_task_classifier_prompt


def task_classifier_node(state: State) -> Command[Literal["executor"]]:
    """
    Classify each task into its type.

    Args:
        state: Current workflow state with todoist_tasks

    Returns:
        Command with updated state routing to executor
    """
    tasks = state.get("todoist_tasks", [])

    if not tasks:
        error_message = HumanMessage(
            content="No tasks available to classify",
            name="task_classifier"
        )
        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )

    try:
        # Import model factory
        from config.model_factory import get_chat_model

        # Generate classification prompt
        prompt = get_task_classifier_prompt(tasks)

        # Get classification from LLM
        model = get_chat_model()
        response = model.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON response
        # Try to extract JSON from response (in case there's extra text)
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            classifications = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in response")

        # Create summary message
        summary = "Task Classifications:\n"
        for task_id, task_type in classifications.items():
            # Find task content for display
            task = next((t for t in tasks if t['id'] == task_id), None)
            if task:
                summary += f"- {task['content']}: {task_type}\n"
            else:
                summary += f"- Task {task_id}: {task_type}\n"

        result_message = HumanMessage(
            content=summary,
            name="task_classifier"
        )

        return Command(
            update={
                "messages": [result_message],
                "task_classifications": classifications,
            },
            goto="executor"
        )

    except Exception as e:
        error_message = HumanMessage(
            content=f"Error classifying tasks: {str(e)}",
            name="task_classifier"
        )

        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )
