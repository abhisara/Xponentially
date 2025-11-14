"""
Planner Node
Creates execution plan for task processing workflow.
"""
import json
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from helpers.state import State
from prompts.agent_descriptions import format_agent_guidelines_for_planning
from prompts.templates import get_planner_prompt


def planner_node(state: State) -> Command[Literal["executor"]]:
    """
    Create execution plan for processing tasks.

    Args:
        state: Current workflow state

    Returns:
        Command with updated plan routing to executor
    """
    user_query = state.get("user_query", "Process today's Todoist tasks")
    enabled_agents = state.get("enabled_agents") or [
        "todoist_fetcher",
        "task_classifier",
        "research_processor",
        "next_action_processor",
        "markdown_writer"
    ]

    try:
        # Import model factory
        from config.model_factory import get_chat_model

        # Get agent guidelines
        agent_guidelines = format_agent_guidelines_for_planning(enabled_agents)

        # Generate planner prompt
        prompt = get_planner_prompt(enabled_agents, agent_guidelines, user_query)

        # Get plan from LLM (lower temperature for focused planning)
        model = get_chat_model(temperature=0.3)
        response = model.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            plan = json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in planner response")

        # Create plan summary message
        plan_summary = "Created execution plan:\n"
        for step, details in plan.items():
            plan_summary += f"Step {step}: {details['agent']} - {details['action']}\n"

        plan_message = HumanMessage(
            content=plan_summary,
            name="planner"
        )

        return Command(
            update={
                "messages": [plan_message],
                "plan": plan,
                "current_step": 1,
                "replan_attempts": {},
            },
            goto="executor"
        )

    except Exception as e:
        error_message = HumanMessage(
            content=f"Error creating plan: {str(e)}",
            name="planner"
        )

        # Create a simple fallback plan
        fallback_plan = {
            "1": {"agent": "todoist_fetcher", "action": "Fetch today's tasks"},
            "2": {"agent": "task_classifier", "action": "Classify each task"},
            "3": {"agent": "markdown_writer", "action": "Generate report"}
        }

        return Command(
            update={
                "messages": [error_message],
                "plan": fallback_plan,
                "current_step": 1,
                "replan_attempts": {},
            },
            goto="executor"
        )
