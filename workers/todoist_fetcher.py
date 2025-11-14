"""
Todoist Task Fetcher Worker
Fetches today's tasks from the Todoist API.
"""
from datetime import datetime
from typing import Literal
from todoist_api_python.api import TodoistAPI
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from config.config import TODOIST_API_TOKEN
from helpers.state import State


def todoist_fetcher_node(state: State) -> Command[Literal["executor"]]:
    """
    Fetch today's tasks from Todoist API.

    Args:
        state: Current workflow state

    Returns:
        Command with updated state routing to executor
    """
    try:
        # Initialize Todoist API
        api = TodoistAPI(TODOIST_API_TOKEN)

        # Fetch all projects to create project_id -> name mapping
        all_projects = api.get_projects()
        project_id_to_name = {project.id: project.name for project in all_projects}

        # Fetch all active tasks
        all_tasks = api.get_tasks()

        # Get today's date
        today = datetime.now().date()

        # Filter for today's tasks
        today_tasks = []
        for task in all_tasks:
            # Check if task has a due date
            if task.due and task.due.date:
                task_date = datetime.strptime(task.due.date, "%Y-%m-%d").date()

                # Include tasks due today or overdue
                if task_date <= today:
                    today_tasks.append({
                        "id": task.id,
                        "content": task.content,
                        "description": task.description or "",
                        "labels": task.labels,
                        "priority": task.priority,
                        "due_date": task.due.date,
                        "project_id": task.project_id,
                    })

        # Apply task limit if specified
        task_limit = state.get("task_limit")
        if task_limit and task_limit > 0:
            today_tasks = today_tasks[:task_limit]

        # Create result message
        task_summary = f"Fetched {len(today_tasks)} tasks for today:\n"
        for i, task in enumerate(today_tasks, 1):
            task_summary += f"{i}. {task['content']}\n"

        result_message = HumanMessage(
            content=task_summary,
            name="todoist_fetcher"
        )

        # Update state with tasks, project mapping, and message
        return Command(
            update={
                "messages": [result_message],
                "todoist_tasks": today_tasks,
                "project_id_to_name": project_id_to_name,
                "current_task_index": 0,
            },
            goto="executor"
        )

    except Exception as e:
        error_message = HumanMessage(
            content=f"Error fetching Todoist tasks: {str(e)}",
            name="todoist_fetcher"
        )

        return Command(
            update={"messages": [error_message]},
            goto="executor"
        )
