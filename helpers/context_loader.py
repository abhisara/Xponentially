"""
Context File Loader
Discovers and loads context files for tasks based on description keywords.
"""
import os
from typing import Dict, Optional, List, Tuple


# Directory where context files are stored
CONTEXT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "contexts")


# Keyword mappings for context file discovery
CONTEXT_KEYWORDS = {
    "meal_planning.md": ["meal planning", "meal prep", "grocery", "cooking", "recipe"],
    "learning.md": ["learning", "study", "course", "tutorial", "education"],
    # Add more mappings as you create new context files
    # "fitness.md": ["workout", "exercise", "fitness", "gym"],
    # "finance.md": ["budget", "finance", "money", "expense"],
}


def find_context_file(task: dict) -> Optional[str]:
    """
    Find a context file for a task based on keywords in the task description.

    Checks task content (description) for keywords that match available context files.

    Args:
        task: Task dictionary with 'content', 'description', 'labels' fields

    Returns:
        Path to context file if found, None otherwise

    Example:
        task = {"content": "Create meal planning for next week"}
        path = find_context_file(task)  # Returns "contexts/meal_planning.md"
    """
    # Get task text to search (content + description)
    task_content = task.get("content", "").lower()
    task_description = task.get("description", "").lower()
    task_text = f"{task_content} {task_description}"

    # Check each context file's keywords
    for context_filename, keywords in CONTEXT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in task_text:
                context_path = os.path.join(CONTEXT_DIR, context_filename)

                # Only return if file actually exists
                if os.path.exists(context_path):
                    return context_path

    return None


def load_context_for_task(task: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Find and load context file content for a task.

    Args:
        task: Task dictionary

    Returns:
        Tuple of (context_file_path, context_content)
        Returns (None, None) if no context file found

    Example:
        path, content = load_context_for_task(task)
        if content:
            print(f"Loaded context from {path}")
    """
    context_path = find_context_file(task)

    if not context_path:
        return None, None

    try:
        with open(context_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return context_path, content
    except Exception as e:
        # Return error message as content so worker knows what happened
        error_msg = f"Error reading context file {context_path}: {str(e)}"
        return context_path, error_msg


def load_context_file(context_path: str) -> Optional[str]:
    """
    Load a specific context file by path.

    Args:
        context_path: Full path to context file

    Returns:
        File content as string, or None if file doesn't exist
    """
    if not os.path.exists(context_path):
        return None

    try:
        with open(context_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading context file: {str(e)}"


def get_available_contexts() -> Dict[str, str]:
    """
    Get all available context files and their paths.

    Returns:
        Dictionary mapping context names to file paths

    Example:
        {
            "meal_planning": "/path/to/contexts/meal_planning.md",
            "learning": "/path/to/contexts/learning.md"
        }
    """
    if not os.path.exists(CONTEXT_DIR):
        return {}

    contexts = {}

    try:
        for filename in os.listdir(CONTEXT_DIR):
            if filename.endswith('.md') and filename != 'README.md':
                context_name = filename[:-3]  # Remove .md extension
                contexts[context_name] = os.path.join(CONTEXT_DIR, filename)
    except Exception as e:
        print(f"Error listing context files: {e}")

    return contexts


def format_context_for_prompt(context_content: str, context_name: str = "Context") -> str:
    """
    Format context content for inclusion in LLM prompts.

    Args:
        context_content: The content from the context file
        context_name: Name of the context (e.g., "meal_planning")

    Returns:
        Formatted string ready to include in prompt
    """
    if not context_content:
        return ""

    return f"""
## {context_name.replace('_', ' ').title()} Context

The following context information is available for this task:

{context_content}

---

Please use the above context to inform your response and ensure continuity with past work on similar tasks.
"""


def get_context_summary() -> str:
    """
    Get a summary of all available context files.

    Returns:
        Formatted string listing all available contexts
    """
    contexts = get_available_contexts()

    if not contexts:
        return "No context files available."

    summary = "Available context files:\n"
    for name, path in contexts.items():
        exists = "✓" if os.path.exists(path) else "✗"
        summary += f"  {exists} {name}\n"

    return summary


# Example usage (for testing)
if __name__ == "__main__":
    # Test with a sample task
    test_task = {
        "content": "Create meal planning for next week",
        "description": "Plan meals for the upcoming week",
        "id": "test123"
    }

    print("Testing context loader...")
    print("-" * 50)

    # Find context
    path, content = load_context_for_task(test_task)

    if path:
        print(f"✓ Found context: {os.path.basename(path)}")
        print(f"  Content length: {len(content)} characters")
        print(f"\nFormatted for prompt:")
        print(format_context_for_prompt(content, "meal_planning"))
    else:
        print("✗ No context found for task")

    print("-" * 50)
    print(get_context_summary())
