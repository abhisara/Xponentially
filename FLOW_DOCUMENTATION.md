# Complete Application Flow Documentation

## Overall Workflow Architecture

```
START → planner → executor → [task_loop] → markdown_writer → END
                ↓
        [todoist_fetcher]
                ↓
        [task_classifier]
                ↓
        [task_loop: process each task individually]
                ↓
        [markdown_writer]
```

---

## Task Type Routing

Based on classification:
- **learning** → `learning_processor`
- **abstract** → `learning_processor`
- **planning** → `planning_processor`
- **research** → `research_processor`
- **short** → `next_action_processor`

---

## 1. LEARNING TASK FLOW

### Function Call Chain:
```
executor_node() 
  → handle_task_loop()
    → learning_processor_node(state)
```

### Data Flow:

#### Step 1: Get Task from State
```python
task = state.get("todoist_tasks")[current_task_index]
task_id = task['id']
task_classification = "learning"  # from task_classifications dict
```

#### Step 2: Load Context (if available)
```python
# Function: load_context_for_task(task)
# Location: helpers/context_loader.py

# Searches for context file based on keywords in task content/description
# Keywords: ["learning", "study", "course", "tutorial", "education"]
# Looks in: contexts/learning.md

context_path, context_content = load_context_for_task(task)
# Returns: (path_to_file, file_content) or (None, None)

# Format context for prompt
context_info = format_context_for_prompt(context_content, "Learning")
# Returns formatted string:
"""
## Learning Context

The following context information is available for this task:

{context_content}

---

Please use the above context to inform your response and ensure continuity with past work on similar tasks.
"""
```

#### Step 3: Extract Task Data
```python
project_name = project_id_to_name.get(task.get('project_id'), "Unknown Project")
comments = task.get('comments', [])  # List of comment dicts with 'posted_at' and 'content'
```

#### Step 4: Generate Learning Plan Prompt
```python
# Function: get_processor_prompt(task_type="learning", task, context, comments, project_name)
# Location: prompts/templates.py

prompt = f"""You are a learning curriculum builder. Create a comprehensive learning path for this educational task.

TASK:
Project: {project_name}
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}
Comments:
  1. ({comment1['posted_at']}): {comment1['content']}
  2. ({comment2['posted_at']}): {comment2['content']}
{context_info if context_info else ""}

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

### 6. Connection to Previous Learning
How this builds on past work or relates to your learning context.

### 7. Insights from Comments
Key points, resources, or guidance from task comments.

Return your learning plan as well-structured markdown. Be comprehensive but concise.
Do NOT include a "Next Steps" section - that will be generated separately.
"""
```

#### Step 5: First LLM Call - Generate Learning Plan
```python
# Function: get_tracked_chat_model(node_name="learning_processor", purpose="learning_path_generation")
# Location: config/model_factory.py

model = get_tracked_chat_model(
    node_name="learning_processor",
    purpose="learning_path_generation"
)
response = model.invoke(prompt)
learning_output = response.content  # Full learning plan markdown
```

#### Step 6: Generate Next Step Prompt
```python
# Function: get_next_step_prompt(task, learning_plan, comments, context)
# Location: prompts/templates.py

next_step_prompt = f"""You are a learning action planner. Your task is to suggest ONE specific, actionable next step.

TASK:
{task['content']}

LEARNING PLAN SUMMARY:
{learning_output}

COMMENTS:
1. ({comment1['posted_at']}): {comment1['content']}
2. ({comment2['posted_at']}): {comment2['content']}

{context_info if context_info else ""}

INSTRUCTIONS:
Based on the learning plan, comments, and any context provided, suggest the SINGLE MOST IMPORTANT next action the user should take RIGHT NOW to make progress on this learning task.

The next step should be:
- Specific and actionable (not vague like "learn more")
- Achievable in one focused work session (1-2 hours max)
- The logical first/next step in the learning path
- Concrete (e.g., "Read Chapter 3 of X", "Watch video at URL", "Build example Y")

OUTPUT:
Return ONLY the next step as 1-2 sentences. Be direct and specific.

Return ONLY the next step, nothing else.
"""
```

#### Step 7: Second LLM Call - Generate Next Step
```python
next_step_model = get_tracked_chat_model(
    node_name="learning_processor",
    purpose="next_step_generation"
)
next_step_response = next_step_model.invoke(next_step_prompt)
next_step = next_step_response.content  # Single actionable step
```

#### Step 8: Write to Markdown File
```python
# Function: create_or_update_learning_task_file(task, project_name, comments, learning_plan, next_step)
# Location: helpers/learning_file_manager.py

filepath, is_new = create_or_update_learning_task_file(
    task=task,
    project_name=project_name,
    comments=comments,
    learning_plan=learning_output,  # From Step 5
    next_step=next_step              # From Step 7
)

# File Location: learning_tasks/{sanitized_task_name}.md

# File Structure:
"""
# {task['content']}

**Project:** {project_name}
**Created:** {created_date}
**Due:** {task.get('due_date', 'No due date')}
**Labels:** {labels_str}

---

## Task Description

{task.get('description', 'No description provided')}

---

## Comments from Todoist

### Comment 1 ({formatted_date})
{comment1['content']}

### Comment 2 ({formatted_date})
{comment2['content']}

---

## Learning Path (Generated: {timestamp})

{learning_output}

### Next Immediate Step

{next_step}

---

*File created: {date} | Last updated: {timestamp}*
"""
```

#### Step 9: Update State and Return
```python
processed_results[task_id] = learning_output
learning_task_files[task_id] = filepath

return Command(
    update={
        "messages": [result_message],
        "processed_results": processed_results,
        "learning_task_files": learning_task_files,
        "task_context_files": task_context_files,
    },
    goto="executor"
)
```

---

## 2. PLANNING TASK FLOW

### Function Call Chain:
```
executor_node()
  → handle_task_loop()
    → planning_processor_node(state)
```

### Data Flow:

#### Step 1: Get Task from State
```python
task = state.get("todoist_tasks")[current_task_index]
task_id = task['id']
task_classification = "planning"
```

#### Step 2: Extract Goal and Steps Taken
```python
goal = task['content']  # Task name IS the goal

# Extract steps from comments
steps_taken = []
for comment in task.get('comments', []):
    steps_taken.append(comment.get('content', '').strip())
# Example: ["Researched competitors", "Created initial wireframes", "Set up project repo"]
```

#### Step 3: Perform Web Search
```python
# Function: perform_web_search(query)
# Location: workers/planning_processor.py

search_query = f"how to {goal} step by step guide checklist"
# Example: "how to launch a mobile app step by step guide checklist"

search_results = perform_web_search(search_query)
# Uses DuckDuckGo search tool
# Returns formatted string with search results (max 2000 chars)
```

#### Step 4: Generate Planning Analysis Prompt
```python
# Function: get_planning_processor_prompt(goal, steps_taken, task_description, project_name, search_results)
# Location: prompts/templates.py

prompt = f"""You are a planning progress analyzer. Your task is to analyze progress toward a goal and identify what remains to be done.

GOAL (from task name):
{goal}

Project: {project_name}
Task Description: {task.get('description', 'None')}

## Steps Taken So Far (from comments):
1. {steps_taken[0]}
2. {steps_taken[1]}
3. {steps_taken[2]}

## Web Search Results (for identifying required steps):
{search_results}

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
```

#### Step 5: LLM Call - Generate Planning Analysis
```python
model = get_tracked_chat_model(
    node_name="planning_processor",
    purpose="planning_analysis"
)
response = model.invoke(prompt)
planning_analysis = response.content  # Full progress summary
```

#### Step 6: Update State and Return
```python
processed_results[task_id] = planning_analysis

return Command(
    update={
        "messages": [result_message],
        "processed_results": processed_results,
    },
    goto="executor"
)
```

**Note:** Planning tasks do NOT write to markdown files. Results are stored in `processed_results` and included in the final markdown report.

---

## 3. RESEARCH TASK FLOW

### Function Call Chain:
```
executor_node()
  → handle_task_loop()
    → research_processor_node(state)
```

### Data Flow:

#### Step 1: Get Task from State
```python
task = state.get("todoist_tasks")[current_task_index]
task_id = task['id']
task_classification = "research"
```

#### Step 2: Generate Research Plan Prompt
```python
# Function: get_processor_prompt(task_type="research", task)
# Location: prompts/templates.py

prompt = f"""You are a research task processor. Analyze this research task and create a research plan.

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
"""
```

#### Step 3: LLM Call - Generate Research Plan
```python
model = get_tracked_chat_model(
    node_name="research_processor",
    purpose="research_processing"
)
response = model.invoke(prompt)
research_plan = response.content
```

#### Step 4: Update State and Return
```python
processed_results[task_id] = research_plan

return Command(
    update={
        "messages": [result_message],
        "processed_results": processed_results,
    },
    goto="executor"
)
```

**Note:** Research tasks do NOT write to markdown files. Results are stored in `processed_results` and included in the final markdown report.

---

## 4. ABSTRACT TASK FLOW

### Function Call Chain:
```
executor_node()
  → handle_task_loop()
    → learning_processor_node(state)  # Abstract tasks use learning processor!
```

### Data Flow:

Abstract tasks follow the **same flow as LEARNING tasks** (see Section 1), but:

1. They are routed to `learning_processor` (not a separate abstract processor)
2. The prompt used is from `get_processor_prompt(task_type="abstract", ...)`

#### Abstract Prompt:
```python
prompt = f"""You are an abstract model builder. Generate insights for this conceptual task.

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
```

**Note:** Abstract tasks DO write to markdown files (same as learning tasks) in `learning_tasks/` directory.

---

## 5. SHORT TASK FLOW

### Function Call Chain:
```
executor_node()
  → handle_task_loop()
    → next_action_processor_node(state)
```

### Data Flow:

#### Step 1: Get Task from State
```python
task = state.get("todoist_tasks")[current_task_index]
task_id = task['id']
task_classification = "short"
```

#### Step 2: Generate Next Action Prompt
```python
# Function: get_processor_prompt(task_type="short", task)
# Location: prompts/templates.py

prompt = f"""You are a next action processor. Suggest the immediate next actionable step for this task.

TASK:
Content: {task['content']}
Description: {task.get('description', 'None')}
Labels: {', '.join(task.get('labels', []))}

OUTPUT:
Return a single sentence describing the concrete next action to take.
Make it specific, actionable, and achievable in one sitting.
"""
```

#### Step 3: LLM Call - Generate Next Action
```python
model = get_chat_model()  # Note: Not tracked, simpler model
response = model.invoke(prompt)
next_action = response.content  # Single sentence
```

#### Step 4: Update State and Return
```python
processed_results[task_id] = next_action

return Command(
    update={
        "messages": [result_message],
        "processed_results": processed_results,
    },
    goto="executor"
)
```

**Note:** Short tasks do NOT write to markdown files. Results are stored in `processed_results` and included in the final markdown report.

---

## 6. FINAL MARKDOWN REPORT FLOW

### Function Call Chain:
```
executor_node()
  → handle_task_loop()  # After all tasks processed
    → markdown_writer_node(state)
```

### Data Flow:

#### Step 1: Collect All Results
```python
tasks = state.get("todoist_tasks", [])
classifications = state.get("task_classifications", {})
processed_results = state.get("processed_results", {})
project_id_to_name = state.get("project_id_to_name", {})
```

#### Step 2: Generate Report Markdown
```python
# Function: markdown_writer_node(state)
# Location: workers/markdown_writer.py

markdown = f"""# Task Processing Report - {today}

**Total Tasks:** {len(tasks)}

---

## 1. {task1['content']}

**Type:** {task1_type}
**Project:** {project_name}
**Description:** {task1['description']}
**Labels:** {', '.join(task1['labels'])}
**Due Date:** {task1['due_date']}
**Priority:** {task1['priority']}

### Processing Result:

{processed_results[task1_id]}

---

## 2. {task2['content']}
...
"""
```

#### Step 3: Write Report File
```python
# File Location: output/task_report_{timestamp}.md

filename = f"task_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
filepath = os.path.join(OUTPUT_DIR, filename)

with open(filepath, 'w') as f:
    f.write(markdown)
```

---

## Summary: Where Data Gets Written

| Task Type | Individual File? | Location | Final Report? |
|-----------|-----------------|----------|--------------|
| **learning** | ✅ Yes | `learning_tasks/{task_name}.md` | ✅ Yes |
| **abstract** | ✅ Yes | `learning_tasks/{task_name}.md` | ✅ Yes |
| **planning** | ❌ No | N/A | ✅ Yes |
| **research** | ❌ No | N/A | ✅ Yes |
| **short** | ❌ No | N/A | ✅ Yes |

---

## Key Variables Expanded

### State Variables:
- `todoist_tasks`: List of task dicts from Todoist API
- `task_classifications`: Dict mapping task_id → classification ("learning", "planning", etc.)
- `current_task_id`: Current task being processed (task-loop mode)
- `current_task_index`: Current task index (legacy mode)
- `processed_results`: Dict mapping task_id → processing result string
- `learning_task_files`: Dict mapping task_id → filepath (for learning/abstract tasks)
- `task_context_files`: Dict mapping task_id → context file path used
- `project_id_to_name`: Dict mapping project_id → project name

### Task Dictionary Structure:
```python
task = {
    'id': '1234567890',
    'content': 'Learn LangGraph',
    'description': 'Study the architecture and build an agent',
    'project_id': '987654321',
    'labels': ['learning', 'ai'],
    'due_date': '2024-11-15',
    'priority': 2,
    'comments': [
        {
            'posted_at': '2024-11-14T10:00:00Z',
            'content': 'Started reading documentation'
        }
    ],
    'created_at': '2024-11-10T08:00:00Z'
}
```

---

## LLM Call Summary

| Task Type | Number of LLM Calls | Purposes |
|-----------|---------------------|----------|
| **learning** | 2 | 1. Generate learning plan<br>2. Generate next step |
| **abstract** | 2 | 1. Generate abstract insights<br>2. Generate next step |
| **planning** | 1 | 1. Analyze progress and generate summary |
| **research** | 1 | 1. Generate research plan |
| **short** | 1 | 1. Generate next action |

---

## Context Loading Logic

Context files are loaded ONLY for learning/abstract tasks:

1. **Keyword Matching**: Searches task content/description for keywords
2. **Available Contexts**:
   - `contexts/learning.md` → keywords: ["learning", "study", "course", "tutorial", "education"]
   - `contexts/meal_planning.md` → keywords: ["meal planning", "meal prep", "grocery", "cooking", "recipe"]
3. **If Found**: Context is formatted and included in the prompt
4. **If Not Found**: Prompt proceeds without context

---

## Executor Routing Logic

The executor uses an LLM to decide routing:

```python
# Prompt: get_task_loop_executor_prompt()
# Checks:
# - Task classification
# - Processing history (which workers already processed this task)
# - Last worker output
# - Tasks remaining

# Returns JSON:
{
    "goto": "worker_name_or_task_complete",
    "reason": "Why this routing decision",
    "is_complete": true/false
}
```

**Fallback Routing** (if LLM returns invalid worker):
- `planning` → `planning_processor`
- `learning` or `abstract` → `learning_processor`
- `research` → `research_processor`
- `short` → `next_action_processor`

