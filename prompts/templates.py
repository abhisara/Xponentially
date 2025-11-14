"""
Prompt templates for planner and executor nodes.
"""


def get_planner_prompt(enabled_agents: list, agent_guidelines: str, user_query: str) -> str:
    """
    Creates the planner prompt that generates the execution plan.

    Args:
        enabled_agents: List of available worker names
        agent_guidelines: Detailed guidelines for each agent
        user_query: User's request

    Returns:
        Formatted planner prompt
    """
    return f"""You are a task processing planner. Your job is to create a task-loop execution plan for processing Todoist tasks.

USER REQUEST:
{user_query}

AVAILABLE AGENTS:
{agent_guidelines}

VALID AGENT NAMES (use EXACTLY these names in your plan):
- todoist_fetcher
- task_classifier
- research_processor
- next_action_processor
- markdown_writer

PLANNING INSTRUCTIONS:
1. The workflow has two phases:
   - SETUP: fetch tasks → classify all tasks
   - TASK LOOP: process each task individually based on its type → generate report

2. In the TASK LOOP phase:
   - Each task will be processed ONE AT A TIME
   - The executor will intelligently route each task to appropriate workers based on its type
   - After a worker processes a task, the executor will check if the task needs more processing
   - Once a task is complete, the next task begins

3. Available processors for different task types:
   - research_processor: For research, learning, and abstract tasks
   - next_action_processor: For short, planning tasks

OUTPUT FORMAT:
Return a JSON object with setup steps and loop configuration:
{{
  "1": {{"agent": "todoist_fetcher", "action": "Fetch today's tasks from Todoist"}},
  "2": {{"agent": "task_classifier", "action": "Classify all tasks into types"}},
  "3": {{"agent": "task_loop", "action": "Process each task individually with intelligent routing"}},
  "4": {{"agent": "markdown_writer", "action": "Generate final markdown report"}}
}}

IMPORTANT:
- Step 3 should always be "task_loop" - this signals the executor to enter task processing mode
- Use ONLY the agent names from the VALID AGENT NAMES list
- The executor will handle per-task routing automatically

Return ONLY the JSON object, no other text.
"""


def get_executor_prompt(
    plan: dict,
    current_step: int,
    agent_guidelines: str,
    last_messages: str,
    last_reason: str = None
) -> str:
    """
    Creates the executor prompt for routing decisions.

    Args:
        plan: The execution plan from planner
        current_step: Current step number
        agent_guidelines: Agent capability descriptions
        last_messages: Recent message history
        last_reason: Previous executor decision reason

    Returns:
        Formatted executor prompt
    """
    current_step_info = plan.get(str(current_step), {})

    context = f"\nPrevious decision reason: {last_reason}" if last_reason else ""

    return f"""You are the executor. Your job is to decide which agent to invoke next based on the current plan step.

CURRENT PLAN STEP: {current_step}
Planned agent: {current_step_info.get('agent', 'unknown')}
Planned action: {current_step_info.get('action', 'unknown')}

AVAILABLE AGENTS:
{agent_guidelines}

VALID AGENT NAMES (use EXACTLY these names):
- todoist_fetcher
- task_classifier
- research_processor
- next_action_processor
- markdown_writer
- planner (for replanning)
- END (when workflow is complete)

RECENT MESSAGES:
{last_messages}
{context}

DECISION INSTRUCTIONS:
1. Analyze the last message to determine if the current step succeeded
2. Decide whether to proceed with the planned agent or if replanning is needed
3. If the step is complete, move to the next step in the plan
4. If all steps are complete, route to END

OUTPUT FORMAT:
Return a JSON object with exactly 4 fields:
{{
  "replan": false,
  "goto": "agent_name_or_END",
  "reason": "One sentence explaining this decision",
  "query": "Exact instruction for the chosen agent"
}}

IMPORTANT RULES:
- Set replan=true ONLY if you're completely blocked and need a new plan
- Set goto to EXACTLY one of the valid agent names listed above (or "END")
- DO NOT invent new agent names - use only the names from the VALID AGENT NAMES list
- Provide a clear reason for your decision
- Make the query specific and actionable

Return ONLY the JSON object, no other text.
"""


def get_task_loop_executor_prompt(
    current_task: dict,
    task_classification: str,
    processing_history: list,
    last_worker_output: str,
    agent_guidelines: str,
    tasks_remaining: int
) -> str:
    """
    Creates the executor prompt for task-loop routing decisions.

    Args:
        current_task: The task being processed
        task_classification: The type classification for this task
        processing_history: List of workers that have already processed this task
        last_worker_output: Output from the last worker
        agent_guidelines: Agent capability descriptions
        tasks_remaining: Number of tasks left to process

    Returns:
        Formatted task-loop executor prompt
    """
    history_text = ", ".join(processing_history) if processing_history else "None yet"

    return f"""You are the task-loop executor. Your job is to intelligently route individual tasks to appropriate workers and determine when tasks are complete.

CURRENT TASK:
ID: {current_task['id']}
Content: {current_task['content']}
Description: {current_task.get('description', 'None')}
Classification: {task_classification}
Priority: {current_task['priority']}

PROCESSING HISTORY FOR THIS TASK:
Workers that have processed it: {history_text}

LAST WORKER OUTPUT:
{last_worker_output if last_worker_output else "Task just entered the loop"}

AVAILABLE WORKERS:
{agent_guidelines}

VALID WORKER NAMES:
- research_processor (for research, learning, abstract tasks)
- next_action_processor (for short, planning tasks)
- task_complete (signals this task is fully processed, move to next task)

TASKS REMAINING: {tasks_remaining} (including current)

ROUTING DECISION INSTRUCTIONS:
1. **First, determine if the current task is complete:**
   - Has it been processed appropriately for its type?
   - Does the output satisfy the task requirements?
   - Does it need additional processing from another worker?

2. **If task is complete:**
   - Set goto="task_complete"
   - This will move to the next task in the list

3. **If task needs more processing:**
   - Choose the appropriate worker based on:
     * Task classification ({task_classification})
     * What has already been done (history: {history_text})
     * What still needs to be done
   - DO NOT send to a worker it's already visited unless absolutely necessary
   - Match task type to worker:
     * research/learning/abstract → research_processor
     * short/planning → next_action_processor

OUTPUT FORMAT:
Return a JSON object:
{{
  "goto": "worker_name_or_task_complete",
  "reason": "One sentence explaining why this task is complete OR why it needs this worker",
  "is_complete": true_or_false
}}

IMPORTANT RULES:
- Use ONLY the worker names from VALID WORKER NAMES list
- Set is_complete=true when task is done and goto="task_complete"
- Set is_complete=false when task needs more work
- Don't send a task to the same worker twice unless critical
- Be decisive: most tasks should be complete after 1-2 workers

Return ONLY the JSON object, no other text.
"""


def get_task_classifier_prompt(tasks: list) -> str:
    """
    Creates prompt for classifying task types.

    Args:
        tasks: List of task objects with content, description, labels

    Returns:
        Formatted classification prompt
    """
    task_info = []
    for i, task in enumerate(tasks):
        task_info.append(
            f"Task {i+1} (ID: {task['id']}):\n"
            f"  Content: {task['content']}\n"
            f"  Description: {task.get('description', 'None')}\n"
            f"  Labels: {', '.join(task.get('labels', []))}\n"
        )

    tasks_text = "\n".join(task_info)

    return f"""You are a task classifier. Analyze each task and classify it into one of these types:

TASK TYPES:
- research: Tasks requiring web search, reading notes, or gathering information
- planning: Tasks requiring structured planning methodology or breaking down a project
- short: Simple tasks that need a clear next action step
- learning: Educational tasks for building knowledge or skills
- abstract: Tasks involving model building, asking questions, finding parallels, or conceptual thinking

TASKS TO CLASSIFY:
{tasks_text}

OUTPUT FORMAT:
Return a JSON object mapping task IDs to their types:
{{
  "task_id_1": "research",
  "task_id_2": "short",
  "task_id_3": "learning"
}}

Analyze each task carefully and assign the most appropriate type. Return ONLY the JSON object, no other text.
"""


def get_processor_prompt(task_type: str, task: dict) -> str:
    """
    Creates prompt for specialized task processors.

    Args:
        task_type: Type of task (research/planning/short/learning/abstract)
        task: Task object with content and metadata

    Returns:
        Formatted processor prompt
    """
    prompts = {
        "research": f"""You are a research task processor. Analyze this research task and create a research plan.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

OUTPUT:
Generate a research plan that includes:
1. Key questions to investigate
2. Topics to explore
3. Types of sources needed

Return your analysis as a structured text response.
""",

        "short": f"""You are a next action processor. Suggest the immediate next actionable step for this task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

OUTPUT:
Return a single sentence describing the concrete next action to take.
Make it specific, actionable, and achievable in one sitting.
""",

        "planning": f"""You are a planning methodology processor. Create a structured plan for this task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

OUTPUT:
Generate a structured plan with:
1. Goal clarification
2. Key milestones
3. Dependencies and prerequisites
4. Success criteria

Return your plan as structured text.
""",

        "learning": f"""You are a learning curriculum builder. Create a learning path for this educational task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

OUTPUT:
Generate a learning plan with:
1. Current topic focus
2. Prerequisites to cover
3. Next learning steps
4. Practice/application ideas

Return your curriculum as structured text.
""",

        "abstract": f"""You are an abstract model builder. Generate insights for this conceptual task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

OUTPUT:
Generate:
1. Key questions to explore
2. Parallels or analogies
3. Real-world applications
4. Different perspectives or stories

Return your analysis as structured text.
"""
    }

    return prompts.get(task_type, prompts["short"])
