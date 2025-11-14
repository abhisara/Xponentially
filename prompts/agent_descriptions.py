"""
Agent metadata and descriptions for task processing workers.
"""
from typing import Dict, Any, List


def get_agent_descriptions() -> Dict[str, Dict[str, Any]]:
    """
    Returns metadata for all available worker agents.

    Each agent has:
    - name: Display name
    - capability: What it does
    - use_when: When to use it
    - limitations: What it can't do
    - output_format: What it returns
    """
    return {
        "todoist_fetcher": {
            "name": "Todoist Task Fetcher",
            "capability": "Fetches today's tasks from Todoist API",
            "use_when": "At the beginning of workflow to retrieve all tasks",
            "limitations": "Cannot modify tasks, only reads them",
            "output_format": "List of task objects with content, description, labels, due dates",
        },
        "task_classifier": {
            "name": "Task Type Classifier",
            "capability": "Classifies each task into one of five types: research, planning, short, learning, or abstract",
            "use_when": "After fetching tasks, to determine how each should be processed",
            "limitations": "Can only classify, cannot process tasks",
            "output_format": "Dictionary mapping task IDs to task types",
        },
        "research_processor": {
            "name": "Research Task Processor",
            "capability": "Analyzes research tasks and identifies what needs to be researched",
            "use_when": "For tasks classified as 'research' type",
            "limitations": "Does not perform actual web search (placeholder for now)",
            "output_format": "Research plan with key questions and topics to investigate",
        },
        "next_action_processor": {
            "name": "Next Action Processor",
            "capability": "Suggests the immediate next actionable step for short tasks",
            "use_when": "For tasks classified as 'short' type that need a clear next step",
            "limitations": "Only suggests one next action, doesn't create multi-step plans",
            "output_format": "Single sentence describing the next action to take",
        },
        "planning_processor": {
            "name": "Planning Methodology Processor",
            "capability": "Applies structured planning methodology to planning tasks",
            "use_when": "For tasks classified as 'planning' type",
            "limitations": "Requires user's planning methodology to be defined",
            "output_format": "Structured plan following user's methodology (placeholder for now)",
        },
        "learning_processor": {
            "name": "Learning Curriculum Builder",
            "capability": "Creates learning path for educational tasks",
            "use_when": "For tasks classified as 'learning' type",
            "limitations": "Cannot access external learning resources yet",
            "output_format": "Learning plan with topics and suggested next steps (placeholder for now)",
        },
        "abstract_modeler": {
            "name": "Abstract Model Builder",
            "capability": "Generates questions, parallels, stories, and real-world applications for abstract concepts",
            "use_when": "For tasks classified as 'abstract' type that involve model building",
            "limitations": "Requires task comments to be available for full analysis",
            "output_format": "Questions, parallels, stories, and applications (placeholder for now)",
        },
        "markdown_writer": {
            "name": "Markdown Report Generator",
            "capability": "Generates formatted markdown report from all processed task results",
            "use_when": "After all tasks have been processed by specialized workers",
            "limitations": "Can only format existing results, cannot process tasks",
            "output_format": "Markdown formatted report with sections per task",
        },
    }


def format_agent_list_for_planning(enabled_agents: List[str]) -> str:
    """
    Format agent list for inclusion in planner prompt.
    """
    descriptions = get_agent_descriptions()
    agent_list = []

    for agent_name in enabled_agents:
        if agent_name in descriptions:
            agent = descriptions[agent_name]
            agent_list.append(
                f"- {agent_name}: {agent['capability']}"
            )

    return "\n".join(agent_list)


def format_agent_guidelines_for_planning(enabled_agents: List[str]) -> str:
    """
    Format detailed agent guidelines for planner.
    """
    descriptions = get_agent_descriptions()
    guidelines = []

    for agent_name in enabled_agents:
        if agent_name in descriptions:
            agent = descriptions[agent_name]
            guideline = f"""
{agent['name']}:
- Use when: {agent['use_when']}
- Limitations: {agent['limitations']}
- Output: {agent['output_format']}
"""
            guidelines.append(guideline.strip())

    return "\n\n".join(guidelines)


def format_agent_guidelines_for_executor(enabled_agents: List[str]) -> str:
    """
    Format agent guidelines for executor decision-making.
    """
    descriptions = get_agent_descriptions()
    guidelines = []

    for agent_name in enabled_agents:
        if agent_name in descriptions:
            agent = descriptions[agent_name]
            guideline = f"- {agent_name}: {agent['capability']}. Use when: {agent['use_when']}"
            guidelines.append(guideline)

    return "\n".join(guidelines)
