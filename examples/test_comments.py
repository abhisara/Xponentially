"""
Example script demonstrating how to fetch task comments.
"""
import sys
sys.path.append('..')

from helpers.todoist_helpers import (
    get_task_comments,
    format_comments_for_display,
    get_task_with_comments
)


def example_1_basic_comments():
    """Example 1: Fetch comments for a task"""
    print("=" * 60)
    print("Example 1: Fetch comments for a task")
    print("=" * 60)

    # Replace with an actual task ID from your Todoist
    task_id = "YOUR_TASK_ID_HERE"

    try:
        comments = get_task_comments(task_id)
        print(f"\nFound {len(comments)} comments\n")

        for i, comment in enumerate(comments, 1):
            print(f"\nComment {i}:")
            print(f"  ID: {comment['id']}")
            print(f"  Posted: {comment['posted_at']}")
            print(f"  Content: {comment['content'][:100]}...")  # First 100 chars

    except Exception as e:
        print(f"Error: {e}")


def example_2_formatted_display():
    """Example 2: Get formatted comments"""
    print("\n" + "=" * 60)
    print("Example 2: Formatted comments display")
    print("=" * 60)

    task_id = "YOUR_TASK_ID_HERE"

    try:
        comments = get_task_comments(task_id)
        formatted = format_comments_for_display(comments)
        print(f"\n{formatted}")

    except Exception as e:
        print(f"Error: {e}")


def example_3_task_with_comments():
    """Example 3: Get task along with its comments"""
    print("\n" + "=" * 60)
    print("Example 3: Fetch task with comments")
    print("=" * 60)

    task_id = "YOUR_TASK_ID_HERE"

    try:
        task_data = get_task_with_comments(task_id)

        if task_data:
            print(f"\nTask: {task_data['content']}")
            print(f"Description: {task_data['description']}")
            print(f"Priority: {task_data['priority']}")
            print(f"Labels: {', '.join(task_data['labels'])}")
            print(f"Comment count: {task_data['comment_count']}")
            print(f"\nActual comments fetched: {len(task_data['comments'])}")

            # Display comments
            if task_data['comments']:
                print("\nComments:")
                print(format_comments_for_display(task_data['comments']))
        else:
            print("Task not found")

    except Exception as e:
        print(f"Error: {e}")


def example_4_fetch_from_todays_tasks():
    """Example 4: Fetch comments for all today's tasks"""
    print("\n" + "=" * 60)
    print("Example 4: Fetch comments for today's tasks")
    print("=" * 60)

    from datetime import datetime
    from todoist_api_python.api import TodoistAPI
    from config.config import TODOIST_API_TOKEN

    try:
        api = TodoistAPI(TODOIST_API_TOKEN)
        all_tasks = api.get_tasks()
        today = datetime.now().date()

        # Get today's tasks
        today_tasks = []
        for task in all_tasks:
            if task.due and task.due.date:
                task_date = datetime.strptime(task.due.date, "%Y-%m-%d").date()
                if task_date <= today:
                    today_tasks.append(task)

        print(f"\nFound {len(today_tasks)} tasks for today")

        # Fetch comments for each task
        for task in today_tasks[:3]:  # Limit to first 3 tasks
            print(f"\n{'─' * 60}")
            print(f"Task: {task.content}")
            print(f"Comment count: {task.comment_count}")

            if task.comment_count > 0:
                comments = get_task_comments(task.id)
                print(format_comments_for_display(comments))
            else:
                print("No comments")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Uncomment the examples you want to run

    # example_1_basic_comments()
    # example_2_formatted_display()
    # example_3_task_with_comments()
    example_4_fetch_from_todays_tasks()
