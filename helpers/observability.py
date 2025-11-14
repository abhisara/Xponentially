"""
Observability helpers for tracking execution, LLM calls, and state changes.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


@dataclass
class ExecutionEvent:
    """Tracks execution of a single node/worker."""

    node_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    task_id: Optional[str] = None
    task_index: Optional[int] = None
    total_tasks: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self):
        """Mark the event as finished and calculate duration."""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "node_name": self.node_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "task_id": self.task_id,
            "task_index": self.task_index,
            "total_tasks": self.total_tasks,
            "metadata": self.metadata,
        }


@dataclass
class LLMCallInfo:
    """Tracks a single LLM API call."""

    timestamp: datetime
    node_name: str
    model_name: str
    temperature: float
    prompt_length: int
    response_length: int
    duration_seconds: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    purpose: Optional[str] = None  # e.g., "routing_decision", "task_processing"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "node_name": self.node_name,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "prompt_length": self.prompt_length,
            "response_length": self.response_length,
            "duration_seconds": self.duration_seconds,
            "tokens_used": self.tokens_used,
            "cost_estimate": self.cost_estimate,
            "purpose": self.purpose,
        }


@dataclass
class RoutingDecision:
    """Tracks executor routing decisions."""

    timestamp: datetime
    current_step: int
    planned_agent: str
    chosen_agent: str
    reason: str
    task_id: Optional[str] = None
    task_content: Optional[str] = None
    task_classification: Optional[str] = None
    processing_history: List[str] = field(default_factory=list)
    is_task_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "current_step": self.current_step,
            "planned_agent": self.planned_agent,
            "chosen_agent": self.chosen_agent,
            "reason": self.reason,
            "task_id": self.task_id,
            "task_content": self.task_content,
            "task_classification": self.task_classification,
            "processing_history": self.processing_history,
            "is_task_complete": self.is_task_complete,
        }


class ExecutionTracker:
    """Singleton tracker for managing execution events."""

    _instance = None
    _events: List[ExecutionEvent] = []
    _current_event: Optional[ExecutionEvent] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def start_node(cls, node_name: str, task_id: Optional[str] = None,
                   task_index: Optional[int] = None, total_tasks: Optional[int] = None,
                   **metadata) -> ExecutionEvent:
        """Start tracking a node execution."""
        event = ExecutionEvent(
            node_name=node_name,
            start_time=datetime.now(),
            task_id=task_id,
            task_index=task_index,
            total_tasks=total_tasks,
            metadata=metadata
        )
        cls._events.append(event)
        cls._current_event = event
        return event

    @classmethod
    def finish_current_node(cls):
        """Finish the current node execution."""
        if cls._current_event:
            cls._current_event.finish()
            cls._current_event = None

    @classmethod
    def get_events(cls) -> List[ExecutionEvent]:
        """Get all execution events."""
        return cls._events.copy()

    @classmethod
    def reset(cls):
        """Reset tracker for new execution."""
        cls._events = []
        cls._current_event = None


class LLMCallTracker:
    """Singleton tracker for managing LLM calls."""

    _instance = None
    _calls: List[LLMCallInfo] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def record_call(cls, node_name: str, model_name: str, temperature: float,
                   prompt_length: int, response_length: int,
                   duration_seconds: Optional[float] = None,
                   purpose: Optional[str] = None) -> LLMCallInfo:
        """Record an LLM API call."""
        call_info = LLMCallInfo(
            timestamp=datetime.now(),
            node_name=node_name,
            model_name=model_name,
            temperature=temperature,
            prompt_length=prompt_length,
            response_length=response_length,
            duration_seconds=duration_seconds,
            purpose=purpose
        )
        cls._calls.append(call_info)
        return call_info

    @classmethod
    def get_calls(cls) -> List[LLMCallInfo]:
        """Get all LLM calls."""
        return cls._calls.copy()

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get statistics about LLM usage."""
        calls = cls._calls
        if not calls:
            return {"total_calls": 0}

        total_calls = len(calls)
        total_duration = sum(c.duration_seconds for c in calls if c.duration_seconds)
        avg_duration = total_duration / total_calls if total_calls > 0 else 0

        calls_by_node = {}
        for call in calls:
            calls_by_node[call.node_name] = calls_by_node.get(call.node_name, 0) + 1

        return {
            "total_calls": total_calls,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "calls_by_node": calls_by_node,
            "models_used": list(set(c.model_name for c in calls)),
        }

    @classmethod
    def reset(cls):
        """Reset tracker for new execution."""
        cls._calls = []


def create_enhanced_message_metadata(
    node_name: str,
    task_id: Optional[str] = None,
    task_index: Optional[int] = None,
    total_tasks: Optional[int] = None,
    execution_duration: Optional[float] = None,
    executor_reasoning: Optional[str] = None,
    **extra_metadata
) -> Dict[str, Any]:
    """
    Create standardized metadata dictionary for messages.

    Args:
        node_name: Name of the node/worker creating the message
        task_id: ID of the task being processed
        task_index: Current task number (0-indexed)
        total_tasks: Total number of tasks
        execution_duration: How long the node took to execute
        executor_reasoning: Executor's reasoning for routing decision
        **extra_metadata: Any additional metadata

    Returns:
        Dictionary with standardized metadata
    """
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "node_name": node_name,
    }

    if task_id:
        metadata["task_id"] = task_id
    if task_index is not None:
        metadata["task_index"] = task_index
        metadata["task_number"] = task_index + 1  # 1-indexed for display
    if total_tasks:
        metadata["total_tasks"] = total_tasks
        if task_index is not None:
            metadata["progress_percentage"] = ((task_index + 1) / total_tasks) * 100
    if execution_duration:
        metadata["execution_duration_seconds"] = execution_duration
    if executor_reasoning:
        metadata["executor_reasoning"] = executor_reasoning

    # Add any extra metadata
    metadata.update(extra_metadata)

    return metadata


def format_state_for_inspection(state: Dict[str, Any]) -> str:
    """
    Format state dictionary as readable JSON for inspection.

    Args:
        state: State dictionary

    Returns:
        Formatted JSON string
    """
    # Create a copy to avoid modifying original
    state_copy = dict(state)

    # Convert non-serializable objects to strings
    for key, value in state_copy.items():
        if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            state_copy[key] = str(value)

    return json.dumps(state_copy, indent=2, default=str)
