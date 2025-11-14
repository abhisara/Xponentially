"""
Executor Node
Routes between workers based on plan and current state.
Supports both linear plan execution and intelligent task-loop routing.
Includes comprehensive observability and decision tracking.
"""
import json
from datetime import datetime
from typing import Literal, Union
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from helpers.observability import RoutingDecision, ExecutionTracker
from prompts.agent_descriptions import format_agent_guidelines_for_executor
from prompts.templates import get_executor_prompt, get_task_loop_executor_prompt


# Maximum replan attempts per step
MAX_REPLANS = 2


def executor_node(state: State) -> Command[Union[
    Literal["todoist_fetcher"],
    Literal["task_classifier"],
    Literal["research_processor"],
    Literal["next_action_processor"],
    Literal["markdown_writer"],
    Literal["planner"],
    Literal["__end__"]
]]:
    """
    Decide which worker to invoke next.

    Supports two modes:
    1. Linear plan execution (steps 1, 2, 4, ...)
    2. Task-loop routing (step 3) - intelligently routes individual tasks

    Args:
        state: Current workflow state

    Returns:
        Command routing to appropriate worker or END
    """
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)

    # Check if we've completed all steps
    if str(current_step) not in plan:
        # All steps complete
        completion_message = HumanMessage(
            content="All plan steps completed. Workflow finished.",
            name="executor"
        )
        return Command(
            update={"messages": [completion_message]},
            goto="__end__"
        )

    # Get current step info
    step_info = plan.get(str(current_step), {})
    planned_agent = step_info.get("agent", "unknown")

    # CHECK IF WE'RE IN TASK-LOOP MODE
    if planned_agent == "task_loop":
        return handle_task_loop(state)
    else:
        return handle_linear_plan(state, planned_agent)


def handle_task_loop(state: State) -> Command:
    """
    Handle intelligent per-task routing in task-loop mode.

    This mode:
    - Processes one task at a time
    - Routes based on task type and processing history
    - Asks LLM if task needs more processing
    - Moves to next task when complete
    """
    todoist_tasks = state.get("todoist_tasks", [])
    current_task_index = state.get("current_task_index", 0)
    task_classifications = state.get("task_classifications", {})
    task_processing_history = state.get("task_processing_history", {})
    task_completion_status = state.get("task_completion_status", {})
    processed_results = state.get("processed_results", {})
    messages = state.get("messages", [])
    enabled_agents = state.get("enabled_agents") or [
        "research_processor",
        "next_action_processor"
    ]

    # Check if all tasks are processed
    if current_task_index >= len(todoist_tasks):
        completion_message = HumanMessage(
            content=f"All {len(todoist_tasks)} tasks have been processed. Moving to report generation.",
            name="executor"
        )
        return Command(
            update={
                "messages": [completion_message],
                "current_step": state.get("current_step", 3) + 1  # Move to next step (markdown_writer)
            },
            goto="executor"
        )

    # Get current task
    current_task = todoist_tasks[current_task_index]
    task_id = current_task['id']
    task_classification = task_classifications.get(task_id, "short")

    # Initialize history for this task if needed
    if task_id not in task_processing_history:
        task_processing_history[task_id] = []

    processing_history = task_processing_history[task_id]

    # Get last worker output for this task
    last_worker_output = ""
    if messages:
        # Look for most recent message from a processor
        for msg in reversed(messages):
            if hasattr(msg, 'name') and msg.name in ['research_processor', 'next_action_processor']:
                last_worker_output = msg.content[:500]  # First 500 chars
                break

    try:
        # Start tracking this executor execution
        exec_event = ExecutionTracker.start_node(
            node_name="executor (task-loop)",
            task_id=task_id,
            task_index=current_task_index,
            total_tasks=len(todoist_tasks),
            mode="task_loop"
        )

        from config.model_factory import get_tracked_chat_model

        # Get agent guidelines
        agent_guidelines = format_agent_guidelines_for_executor(enabled_agents)

        # Calculate tasks remaining
        tasks_remaining = len(todoist_tasks) - current_task_index

        # Generate task-loop executor prompt
        prompt = get_task_loop_executor_prompt(
            current_task=current_task,
            task_classification=task_classification,
            processing_history=processing_history,
            last_worker_output=last_worker_output,
            agent_guidelines=agent_guidelines,
            tasks_remaining=tasks_remaining
        )

        # Get routing decision from LLM with tracking
        model = get_tracked_chat_model(
            node_name="executor",
            temperature=0.2,
            purpose="task_loop_routing"
        )
        response = model.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            decision = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in executor response")

        # Extract decision fields
        goto_worker = decision.get("goto", "task_complete")
        reason = decision.get("reason", "No reason provided")
        is_complete = decision.get("is_complete", False)

        # Log routing decision
        routing_decision = RoutingDecision(
            timestamp=datetime.now(),
            current_step=state.get("current_step", 3),
            planned_agent="task_loop",
            chosen_agent=goto_worker,
            reason=reason,
            task_id=task_id,
            task_content=current_task['content'],
            task_classification=task_classification,
            processing_history=processing_history.copy(),
            is_task_complete=is_complete
        )

        # Get or initialize executor decisions list
        executor_decisions = state.get("executor_decisions", [])
        executor_decisions.append(routing_decision.to_dict())

        # Finish execution event
        exec_event.finish()
        execution_timeline = state.get("execution_timeline", [])
        execution_timeline.append(exec_event.to_dict())

        # HANDLE TASK COMPLETION
        if goto_worker == "task_complete" or is_complete:
            # Mark task as complete
            task_completion_status[task_id] = True

            completion_message = HumanMessage(
                content=f"✓ Task '{current_task['content']}' completed after {len(processing_history)} worker(s). "
                        f"Reason: {reason}. Moving to next task...",
                name="executor"
            )

            # Move to next task
            return Command(
                update={
                    "messages": [completion_message],
                    "current_task_index": current_task_index + 1,
                    "current_task_id": None,
                    "task_completion_status": task_completion_status,
                    "task_processing_history": task_processing_history,
                    "executor_decisions": executor_decisions,
                    "execution_timeline": execution_timeline,
                },
                goto="executor"  # Loop back to process next task
            )

        # HANDLE ROUTING TO WORKER
        # Validate worker name
        valid_workers = ["research_processor", "next_action_processor"]
        if goto_worker not in valid_workers:
            error_message = HumanMessage(
                content=f"Invalid worker '{goto_worker}'. Defaulting based on task type '{task_classification}'.",
                name="executor"
            )
            # Default routing based on classification
            if task_classification in ['research', 'learning', 'abstract']:
                goto_worker = "research_processor"
            else:
                goto_worker = "next_action_processor"

        # Add worker to processing history
        if goto_worker not in processing_history:
            processing_history.append(goto_worker)

        routing_message = HumanMessage(
            content=f"→ Routing task '{current_task['content']}' (type: {task_classification}) to {goto_worker}. "
                    f"Reason: {reason}",
            name="executor"
        )

        return Command(
            update={
                "messages": [routing_message],
                "current_task_id": task_id,
                "task_processing_history": task_processing_history,
                "agent_query": f"Process task: {current_task['content']}",
                "executor_decisions": executor_decisions,
                "execution_timeline": execution_timeline,
            },
            goto=goto_worker
        )

    except Exception as e:
        # Fallback routing
        error_message = HumanMessage(
            content=f"Executor error: {str(e)}. Using fallback routing for task {current_task_index + 1}.",
            name="executor"
        )

        # Default routing based on classification
        if task_classification in ['research', 'learning', 'abstract']:
            fallback_worker = "research_processor"
        else:
            fallback_worker = "next_action_processor"

        return Command(
            update={
                "messages": [error_message],
                "current_task_id": task_id,
            },
            goto=fallback_worker
        )


def handle_linear_plan(state: State, planned_agent: str) -> Command:
    """
    Handle linear plan execution for setup steps (fetch, classify) and final step (markdown_writer).

    This is the original executor logic for non-task-loop steps.
    """
    plan = state.get("plan", {})
    current_step = state.get("current_step", 1)
    messages = state.get("messages", [])
    last_reason = state.get("last_reason")
    replan_attempts = state.get("replan_attempts", {})
    enabled_agents = state.get("enabled_agents") or [
        "todoist_fetcher",
        "task_classifier",
        "research_processor",
        "next_action_processor",
        "markdown_writer"
    ]

    try:
        # Start tracking this executor execution
        exec_event = ExecutionTracker.start_node(
            node_name="executor (linear)",
            mode="linear_plan",
            current_step=current_step
        )

        from config.model_factory import get_tracked_chat_model

        # Get last 4 messages for context
        recent_messages = messages[-4:] if len(messages) >= 4 else messages
        last_messages_text = "\n".join([
            f"{msg.name}: {msg.content[:200]}" for msg in recent_messages if hasattr(msg, 'name')
        ])

        # Get agent guidelines
        agent_guidelines = format_agent_guidelines_for_executor(enabled_agents)

        # Generate executor prompt
        prompt = get_executor_prompt(
            plan=plan,
            current_step=current_step,
            agent_guidelines=agent_guidelines,
            last_messages=last_messages_text,
            last_reason=last_reason
        )

        # Get decision from LLM with tracking
        model = get_tracked_chat_model(
            node_name="executor",
            temperature=0.3,
            purpose="linear_plan_routing"
        )
        response = model.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            decision = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in executor response")

        # Extract decision fields
        should_replan = decision.get("replan", False)
        goto_agent = decision.get("goto", planned_agent)
        reason = decision.get("reason", "No reason provided")
        agent_query = decision.get("query", "")

        # Log routing decision
        routing_decision = RoutingDecision(
            timestamp=datetime.now(),
            current_step=current_step,
            planned_agent=planned_agent,
            chosen_agent=goto_agent,
            reason=reason,
            is_task_complete=False
        )

        executor_decisions = state.get("executor_decisions", [])
        executor_decisions.append(routing_decision.to_dict())

        # Finish execution event
        exec_event.finish()
        execution_timeline = state.get("execution_timeline", [])
        execution_timeline.append(exec_event.to_dict())

        # Validate worker name - map common mistakes
        worker_name_mapping = {
            "research_task_processor": "research_processor",
            "next_action": "next_action_processor",
            "task_classifier_worker": "task_classifier",
            "markdown_report_writer": "markdown_writer",
        }

        if goto_agent in worker_name_mapping:
            original_name = goto_agent
            goto_agent = worker_name_mapping[goto_agent]
            reason += f" (Mapped {original_name} to {goto_agent})"

        # Validate that the worker exists
        valid_agents = enabled_agents + ["planner", "__end__", "END"]
        if goto_agent not in valid_agents and goto_agent != "__end__" and goto_agent != "END":
            error_message = HumanMessage(
                content=f"Warning: Executor tried to route to invalid worker '{goto_agent}'. Skipping to next step.",
                name="executor"
            )
            return Command(
                update={
                    "messages": [error_message],
                    "current_step": current_step + 1,
                },
                goto="executor"
            )

        # Check replan attempts for this step
        step_replan_count = replan_attempts.get(current_step, 0)

        # Handle replanning
        if should_replan and step_replan_count < MAX_REPLANS:
            replan_attempts[current_step] = step_replan_count + 1

            replan_message = HumanMessage(
                content=f"Requesting replan at step {current_step}. Reason: {reason}",
                name="executor"
            )

            return Command(
                update={
                    "messages": [replan_message],
                    "replan_flag": True,
                    "last_reason": reason,
                    "replan_attempts": replan_attempts,
                },
                goto="planner"
            )

        # Normal routing to worker
        decision_message = HumanMessage(
            content=f"Step {current_step}: Routing to {goto_agent}. Reason: {reason}",
            name="executor"
        )

        # Determine next step
        next_step = current_step + 1 if goto_agent != "__end__" else current_step

        return Command(
            update={
                "messages": [decision_message],
                "agent_query": agent_query,
                "current_step": next_step,
                "last_reason": reason,
                "replan_flag": False,
                "executor_decisions": executor_decisions,
                "execution_timeline": execution_timeline,
            },
            goto=goto_agent if goto_agent != "END" else "__end__"
        )

    except Exception as e:
        # Fallback: proceed with planned agent
        error_message = HumanMessage(
            content=f"Executor error: {str(e)}. Falling back to planned agent: {planned_agent}",
            name="executor"
        )

        return Command(
            update={
                "messages": [error_message],
                "current_step": current_step + 1,
            },
            goto=planned_agent if planned_agent != "END" else "__end__"
        )
