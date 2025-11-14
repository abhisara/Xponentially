"""
Markdown Writer Worker
Generates formatted markdown report from processed task results.
"""
import os
from datetime import datetime
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from config.config import OUTPUT_DIR
from helpers.state import State


def markdown_writer_node(state: State) -> Command[Literal["__end__"]]:
    """
    Generate markdown report from all processed results.

    Args:
        state: Current workflow state with processed_results

    Returns:
        Command routing to END
    """
    tasks = state.get("todoist_tasks", [])
    classifications = state.get("task_classifications", {})
    processed_results = state.get("processed_results", {})
    project_id_to_name = state.get("project_id_to_name", {})

    if not tasks:
        error_message = HumanMessage(
            content="No tasks available to generate report",
            name="markdown_writer"
        )
        return Command(
            update={"messages": [error_message]},
            goto="__end__"
        )

    try:
        # Create markdown content
        today = datetime.now().strftime("%Y-%m-%d")
        markdown = f"# Task Processing Report - {today}\n\n"
        markdown += f"**Total Tasks:** {len(tasks)}\n\n"
        markdown += "---\n\n"

        # Add each task with its processing result
        for i, task in enumerate(tasks, 1):
            task_id = task['id']
            task_type = classifications.get(task_id, "unclassified")
            result = processed_results.get(task_id, "Not yet processed")
            project_name = project_id_to_name.get(task['project_id'], "Unknown Project")

            markdown += f"## {i}. {task['content']}\n\n"
            markdown += f"**Type:** {task_type}\n\n"
            markdown += f"**Project:** {project_name}\n\n"

            if task['description']:
                markdown += f"**Description:** {task['description']}\n\n"

            if task['labels']:
                markdown += f"**Labels:** {', '.join(task['labels'])}\n\n"

            markdown += f"**Due Date:** {task['due_date']}\n\n"
            markdown += f"**Priority:** {task['priority']}\n\n"

            markdown += f"### Processing Result:\n\n"
            markdown += f"{result}\n\n"
            markdown += "---\n\n"

        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Save to file
        filename = f"task_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, 'w') as f:
            f.write(markdown)

        result_message = HumanMessage(
            content=f"Generated markdown report: {filepath}\n\n{markdown}",
            name="markdown_writer"
        )

        return Command(
            update={"messages": [result_message]},
            goto="__end__"
        )

    except Exception as e:
        error_message = HumanMessage(
            content=f"Error generating markdown report: {str(e)}",
            name="markdown_writer"
        )

        return Command(
            update={"messages": [error_message]},
            goto="__end__"
        )
