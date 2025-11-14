"""
Learning Task File Manager
Utilities for creating and managing persistent learning task markdown files.
"""
import os
import re
from datetime import datetime
from typing import Dict, List, Optional


# Learning tasks directory (subdirectory of output)
LEARNING_TASKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "learning_tasks"
)


def sanitize_filename(task_name: str) -> str:
    """
    Convert task name to a safe filename.

    Args:
        task_name: Original task name/content

    Returns:
        Sanitized filename (lowercase, underscores, alphanumeric only)

    Example:
        "Learn LangGraph Architecture!" → "learn_langgraph_architecture"
    """
    # Remove special characters, keep alphanumeric and spaces
    safe_name = re.sub(r'[^\w\s-]', '', task_name)

    # Replace spaces and hyphens with underscores
    safe_name = safe_name.replace(' ', '_').replace('-', '_')

    # Convert to lowercase
    safe_name = safe_name.lower()

    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)

    # Limit length to 100 characters
    safe_name = safe_name[:100]

    # Remove trailing/leading underscores
    safe_name = safe_name.strip('_')

    return safe_name


def format_comments_section(comments: List[Dict]) -> str:
    """
    Format task comments as markdown section.

    Args:
        comments: List of comment dictionaries with 'posted_at' and 'content' fields

    Returns:
        Formatted markdown string
    """
    if not comments or len(comments) == 0:
        return "## Comments from Todoist\n\nNo comments yet.\n\n"

    section = "## Comments from Todoist\n\n"

    for i, comment in enumerate(comments, 1):
        # Format timestamp
        posted_at = comment.get('posted_at', 'Unknown date')
        try:
            # Parse ISO timestamp and make it human-readable
            dt = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
            posted_at_formatted = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            posted_at_formatted = posted_at

        content = comment.get('content', '').strip()

        section += f"### Comment {i} ({posted_at_formatted})\n{content}\n\n"

    return section


def get_learning_task_filepath(task: Dict) -> str:
    """
    Generate filepath for a learning task's markdown file.

    Args:
        task: Task dictionary with 'content' field

    Returns:
        Full absolute path to the markdown file
    """
    filename = f"{sanitize_filename(task['content'])}.md"
    return os.path.join(LEARNING_TASKS_DIR, filename)


def format_task_header(task: Dict, project_name: str) -> str:
    """
    Format the header section of a learning task file.

    Args:
        task: Task dictionary
        project_name: Name of the Todoist project

    Returns:
        Formatted markdown header string
    """
    # Parse created_at timestamp
    created_date = "Unknown"
    if task.get('created_at'):
        try:
            dt = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
            created_date = dt.strftime("%B %d, %Y")
        except:
            created_date = task.get('created_at', 'Unknown')

    # Format labels
    labels_str = ", ".join(task.get('labels', [])) if task.get('labels') else "None"

    header = f"""# {task['content']}

**Project:** {project_name}
**Created:** {created_date}
**Due:** {task.get('due_date', 'No due date')}
**Labels:** {labels_str}

---

## Task Description

{task.get('description', 'No description provided')}

---

"""
    return header


def create_learning_task_file(
    task: Dict,
    project_name: str,
    comments: List[Dict],
    learning_plan: str,
    next_step: str
) -> str:
    """
    Create a new learning task markdown file.

    Args:
        task: Task dictionary
        project_name: Name of the Todoist project
        comments: List of task comments
        learning_plan: LLM-generated learning path
        next_step: LLM-generated next immediate step

    Returns:
        Path to the created file
    """
    # Ensure directory exists
    os.makedirs(LEARNING_TASKS_DIR, exist_ok=True)

    # Get filepath
    filepath = get_learning_task_filepath(task)

    # Get current timestamp
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Build content
    content = format_task_header(task, project_name)
    content += format_comments_section(comments)
    content += f"""---

## Learning Path (Generated: {timestamp})

{learning_plan}

### Next Immediate Step

{next_step}

---

*File created: {datetime.now().strftime("%B %d, %Y")} | Last updated: {timestamp}*
"""

    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def append_to_learning_task_file(
    filepath: str,
    learning_plan: str,
    next_step: str
) -> str:
    """
    Append a new timestamped entry to an existing learning task file.

    Args:
        filepath: Path to existing file
        learning_plan: New LLM-generated learning path
        next_step: New LLM-generated next step

    Returns:
        Path to the updated file
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File does not exist: {filepath}")

    # Read existing content
    with open(filepath, 'r', encoding='utf-8') as f:
        existing_content = f.read()

    # Get current timestamp
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Create new section
    new_section = f"""
---

## Update: {timestamp}

### Learning Path (Revised)

{learning_plan}

### Next Immediate Step

{next_step}
"""

    # Update the "Last updated" line in footer
    updated_content = re.sub(
        r'\*File created: .+ \| Last updated: .+\*',
        f'*File created: {existing_content.split("File created: ")[1].split(" | ")[0]} | Last updated: {timestamp}*',
        existing_content
    )

    # Insert new section before the footer
    footer_pattern = r'\n---\n\n\*File created:'
    if re.search(footer_pattern, updated_content):
        updated_content = re.sub(
            footer_pattern,
            new_section + '\n---\n\n*File created:',
            updated_content
        )
    else:
        # Fallback: just append
        updated_content = existing_content + new_section

    # Write updated content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    return filepath


def create_or_update_learning_task_file(
    task: Dict,
    project_name: str,
    comments: List[Dict],
    learning_plan: str,
    next_step: str
) -> tuple[str, bool]:
    """
    Create new learning task file or update existing one.

    Args:
        task: Task dictionary
        project_name: Name of the Todoist project
        comments: List of task comments
        learning_plan: LLM-generated learning path
        next_step: LLM-generated next step

    Returns:
        Tuple of (filepath, is_new) where is_new is True if file was created
    """
    filepath = get_learning_task_filepath(task)

    if os.path.exists(filepath):
        # Update existing file
        append_to_learning_task_file(filepath, learning_plan, next_step)
        return filepath, False
    else:
        # Create new file
        create_learning_task_file(task, project_name, comments, learning_plan, next_step)
        return filepath, True
