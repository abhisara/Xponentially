"""
State management for the task processing workflow.
"""
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


class State(MessagesState):
    """
    State that flows through the LangGraph workflow.

    Inherits 'messages' from MessagesState for shared message history.
    """
    # Todoist data
    todoist_tasks: Optional[List[Dict[str, Any]]]  # Tasks fetched from API
    project_id_to_name: Optional[Dict[str, str]]  # project_id -> project_name mapping
    current_task_index: Optional[int]  # Which task is currently being processed
    current_task_id: Optional[str]  # ID of task currently being worked on

    # Task processing
    task_classifications: Optional[Dict[str, str]]  # task_id -> type mapping
    processed_results: Optional[Dict[str, str]]  # task_id -> processing output
    task_processing_history: Optional[Dict[str, List[str]]]  # task_id -> [worker names that processed it]
    task_completion_status: Optional[Dict[str, bool]]  # task_id -> is_complete flag

    # Planning and execution
    plan: Optional[Dict[str, Dict[str, Any]]]  # Execution plan from planner
    current_step: Optional[int]  # Current step in the plan
    agent_query: Optional[str]  # Instruction for current worker

    # Control flow
    replan_flag: Optional[bool]  # Signals replanning occurred
    last_reason: Optional[str]  # Previous executor decision reason
    replan_attempts: Optional[Dict[int, int]]  # Per-step replan tracking

    # User input
    user_query: Optional[str]  # Original user request
    enabled_agents: Optional[List[str]]  # Which workers are available
    task_limit: Optional[int]  # Maximum number of tasks to process

    # Observability and tracking
    execution_timeline: Optional[List[Dict[str, Any]]]  # Node execution history with timing
    llm_call_log: Optional[List[Dict[str, Any]]]  # All LLM calls made during execution
    executor_decisions: Optional[List[Dict[str, Any]]]  # Routing decisions with reasoning

    # Context file tracking
    task_context_files: Optional[Dict[str, str]]  # task_id -> context_file_path mapping
