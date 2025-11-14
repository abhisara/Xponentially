"""
Todoist Helper Functions
Utility functions for working with Todoist API.
"""
from typing import List, Dict, Any, Optional
from todoist_api_python.api import TodoistAPI

from config.config import TODOIST_API_TOKEN


def get_task_comments(task_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all comments for a specific task.

    Args:
        task_id: The ID of the task to fetch comments for

    Returns:
        List of comment dictionaries with the following structure:
        {
            "id": str,              # Comment ID
            "task_id": str,         # Task ID (null for project comments)
            "project_id": str,      # Project ID (null for task comments)
            "posted_at": str,       # ISO 8601 datetime when comment was posted
            "content": str,         # Comment text (supports markdown)
            "attachment": dict,     # File attachment metadata (null if none)
        }

    Raises:
        Exception: If there's an error fetching comments from Todoist API

    Example:
        >>> comments = get_task_comments("2995104339")
        >>> for comment in comments:
        ...     print(f"{comment['posted_at']}: {comment['content']}")
    """
    try:
        api = TodoistAPI(TODOIST_API_TOKEN)
        comments = api.get_comments(task_id=task_id)

        # Convert comment objects to dictionaries for easier handling
        comment_list = []
        for comment in comments:
            comment_dict = {
                "id": comment.id,
                "task_id": comment.task_id,
                "project_id": comment.project_id,
                "posted_at": comment.posted_at,
                "content": comment.content,
                "attachment": comment.attachment if hasattr(comment, 'attachment') else None,
            }
            comment_list.append(comment_dict)

        return comment_list

    except Exception as e:
        raise Exception(f"Error fetching comments for task {task_id}: {str(e)}")


def format_comments_for_display(comments: List[Dict[str, Any]]) -> str:
    """
    Format a list of comments into a human-readable string.

    Args:
        comments: List of comment dictionaries

    Returns:
        Formatted string with all comments

    Example:
        >>> comments = get_task_comments("2995104339")
        >>> formatted = format_comments_for_display(comments)
        >>> print(formatted)
    """
    if not comments:
        return "No comments found."

    formatted = f"Found {len(comments)} comment(s):\n\n"

    for i, comment in enumerate(comments, 1):
        # Format the timestamp
        posted_at = comment.get('posted_at', 'Unknown time')
        content = comment.get('content', '')

        formatted += f"Comment {i} ({posted_at}):\n"
        formatted += f"{content}\n"

        # Add attachment info if present
        if comment.get('attachment'):
            attachment = comment['attachment']
            if isinstance(attachment, dict):
                filename = attachment.get('file_name', 'attachment')
                formatted += f"  📎 Attachment: {filename}\n"

        formatted += "\n"

    return formatted.strip()


def get_task_with_comments(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a task along with all its comments.

    Args:
        task_id: The ID of the task

    Returns:
        Dictionary with task details and comments, or None if task not found

    Example:
        >>> task_data = get_task_with_comments("2995104339")
        >>> print(task_data['content'])
        >>> print(f"Comments: {len(task_data['comments'])}")
    """
    try:
        api = TodoistAPI(TODOIST_API_TOKEN)

        # Get the task
        task = api.get_task(task_id=task_id)

        # Get the comments
        comments = get_task_comments(task_id)

        # Combine into a single dictionary
        task_data = {
            "id": task.id,
            "content": task.content,
            "description": task.description or "",
            "priority": task.priority,
            "labels": task.labels,
            "due": task.due.date if task.due else None,
            "project_id": task.project_id,
            "comment_count": task.comment_count,
            "comments": comments,
        }

        return task_data

    except Exception as e:
        print(f"Error fetching task with comments: {str(e)}")
        return None
