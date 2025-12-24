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
1. FIRST, check if the planned agent has already run by looking for a message from that agent
2. If the planned agent has NOT run yet, you MUST route to the planned agent (do not skip steps)
3. If the planned agent HAS run and succeeded, move to the next step in the plan
4. If the planned agent failed or you're blocked, consider replanning
5. If all steps are complete, route to END

CRITICAL: Never skip a step. If the planned agent hasn't executed yet, route to it.

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
- research_processor (for research tasks)
- learning_processor (for learning and abstract tasks)
- planning_processor (for planning tasks - analyzes progress and identifies remaining steps)
- next_action_processor (for short tasks)
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
     * research → research_processor
     * learning/abstract → learning_processor
     * planning → planning_processor
     * short → next_action_processor

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


def get_processor_prompt(task_type: str, task: dict, context: str = None, comments: list = None, project_name: str = None) -> str:
    """
    Creates prompt for specialized task processors.

    Args:
        task_type: Type of task (research/planning/short/learning/abstract)
        task: Task object with content and metadata
        context: Optional context information from context files
        comments: Optional list of task comments
        project_name: Optional project name

    Returns:
        Formatted processor prompt
    """
    # Format comments section if provided
    comments_section = ""
    if comments and len(comments) > 0:
        comments_section = "\nComments:\n"
        for i, comment in enumerate(comments, 1):
            posted_at = comment.get('posted_at', 'Unknown')
            content = comment.get('content', '')
            comments_section += f"  {i}. ({posted_at}): {content}\n"

    # Format project info
    project_info = f"Project: {project_name}\n" if project_name else ""

    # Build learning prompt with conditional sections
    learning_prompt = f"""You are a learning curriculum builder. Create a comprehensive learning path for this educational task.

TASK:
{project_info}Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}
{comments_section}
{context if context else ""}

OUTPUT:
Generate a detailed, well-structured learning plan in markdown format with these sections:

### 1. Learning Objective
What you'll master by completing this task.

### 2. Prerequisites
Knowledge or skills needed before starting (if any).

### 3. Learning Path
Step-by-step curriculum to achieve the objective. Be specific about what to learn in each step.

### 4. Resources
Suggested materials (documentation, tutorials, examples, courses).

### 5. Practice Activities
Hands-on exercises or projects to reinforce learning.
"""

    if context:
        learning_prompt += """
### 6. Connection to Previous Learning
How this builds on past work or relates to your learning context.
"""

    if comments_section:
        learning_prompt += """
### 7. Insights from Comments
Key points, resources, or guidance from task comments.
"""

    learning_prompt += """
Return your learning plan as well-structured markdown. Be comprehensive but concise.
Do NOT include a "Next Steps" section - that will be generated separately.
"""

    prompts = {
        "research": f"""You are a research task processor. Analyze this research task and create a research plan.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

{context if context else ""}

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

{context if context else ""}

OUTPUT:
Return a single sentence describing the concrete next action to take.
Make it specific, actionable, and achievable in one sitting.
""",

        "planning": f"""You are a planning methodology processor. Create a structured plan for this task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

{context if context else ""}

OUTPUT:
Generate a structured plan with:
1. Goal clarification
2. Key milestones
3. Dependencies and prerequisites
4. Success criteria

Return your plan as structured text.
""",

        "learning": learning_prompt,

        "abstract": f"""You are an abstract model builder. Generate insights for this conceptual task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

{context if context else ""}

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


def get_next_step_prompt(task: dict, learning_plan: str, comments: list = None, context: str = None) -> str:
    """
    Creates prompt for generating the next immediate actionable step.

    Args:
        task: Task object with content and metadata
        learning_plan: The learning path generated by the learning processor
        comments: Optional list of task comments
        context: Optional context information from context files

    Returns:
        Formatted prompt for next step generation
    """
    # Format comments section
    comments_section = ""
    if comments and len(comments) > 0:
        comments_section = "\nCOMMENTS:\n"
        for i, comment in enumerate(comments, 1):
            posted_at = comment.get('posted_at', 'Unknown')
            content = comment.get('content', '')
            comments_section += f"{i}. ({posted_at}): {content}\n"

    prompt = f"""You are a learning action planner. Your task is to suggest ONE specific, actionable next step.

TASK:
{task['content']}

LEARNING PLAN SUMMARY:
{learning_plan}

{comments_section if comments_section else ""}

{context if context else ""}

INSTRUCTIONS:
Based on the learning plan, comments, and any context provided, suggest the SINGLE MOST IMPORTANT next action the user should take RIGHT NOW to make progress on this learning task.

The next step should be:
- Specific and actionable (not vague like "learn more")
- Achievable in one focused work session (1-2 hours max)
- The logical first/next step in the learning path
- Concrete (e.g., "Read Chapter 3 of X", "Watch video at URL", "Build example Y")

OUTPUT:
Return ONLY the next step as 1-2 sentences. Be direct and specific.

Example good outputs:
- "Read the LangGraph 'Core Concepts' documentation at https://langchain-ai.github.io/langgraph/concepts/, focusing on the State and MessageGraph sections."
- "Clone the example repository from the first comment and run the basic_agent.py script to see a working implementation."
- "Watch the 15-minute LangChain YouTube tutorial on agents, then try modifying the example code to add a custom tool."

Example bad outputs:
- "Learn about LangGraph" (too vague)
- "Study for 5 hours" (not specific about what to study)
- "Do research" (not actionable)

Return ONLY the next step, nothing else.
"""

    return prompt


def get_planning_processor_prompt(
    goal: str,
    steps_taken: list,
    task_description: str = "",
    project_name: str = "",
    search_results: str = ""
) -> str:
    """
    Creates prompt for planning processor with progress analysis and web search.

    Args:
        goal: The goal from task name
        steps_taken: List of steps already completed (from comments)
        task_description: Optional task description
        project_name: Optional project name
        search_results: Web search results for required steps

    Returns:
        Formatted prompt for planning analysis
    """
    # Format steps taken section
    steps_taken_section = ""
    if steps_taken:
        steps_taken_section = "\n## Steps Taken So Far (from comments):\n"
        for i, step in enumerate(steps_taken, 1):
            steps_taken_section += f"{i}. {step}\n"
    else:
        steps_taken_section = "\n## Steps Taken So Far:\nNo steps documented yet in comments.\n"

    # Format project info
    project_info = f"Project: {project_name}\n" if project_name else ""

    prompt = f"""You are a planning progress analyzer. Your task is to analyze progress toward a goal and identify what remains to be done.

GOAL (from task name):
{goal}

{project_info}
Task Description: {task_description if task_description else "None"}

{steps_taken_section}

## Web Search Results (for identifying required steps):
{search_results if search_results else "No web search results available."}

INSTRUCTIONS:
1. **Analyze the goal**: Understand what needs to be accomplished
2. **Review steps taken**: Summarize what has been completed so far based on the comments
3. **Identify required steps**: Based on the web search results and your knowledge, determine what steps are typically needed to achieve this goal
4. **Compare progress**: Compare what's been done with what's required
5. **Create summary**: Generate a clear summary showing:
   - What has been accomplished
   - What steps remain
   - Progress percentage or status
   - Next critical steps to take

OUTPUT FORMAT:
Provide your analysis in the following structure:

## Progress Summary

### Goal
[Restate the goal clearly]

### Steps Completed
[List and summarize what has been done so far]

### Required Steps (from research)
[Based on web search and best practices, list the typical steps needed]

### Progress Analysis
[Compare completed vs required steps, estimate progress percentage]

### Remaining Steps
[What still needs to be done, prioritized]

### Next Critical Actions
[The 2-3 most important next steps to take]

Be specific, actionable, and honest about progress. If little has been done, say so. If significant progress has been made, acknowledge it.
"""

    return prompt
