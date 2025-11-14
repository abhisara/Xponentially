# Task Context File Templates

This directory contains **example/template** context files. These are NOT used by the system directly.

## Setup Instructions

To use context files in your workflow:

1. **Create the contexts/ directory** (if it doesn't exist):
   ```bash
   mkdir contexts
   ```

2. **Copy templates you want to use**:
   ```bash
   cp contexts_examples/meal_planning.md contexts/
   cp contexts_examples/learning.md contexts/
   ```

3. **Customize the files** with your personal information

4. **Your contexts/ folder is private** - it's in `.gitignore` and won't be committed to git

---

# About Context Files

Context files provide continuity across task executions.

## How Context Files Work

Context files are Markdown documents that workers can read to understand preferences, history, and context for recurring tasks.

### Discovery Mechanism

Workers automatically discover context files by checking **task descriptions** for keywords:

- Task contains "meal planning" → loads `meal_planning.md`
- Task contains "learning" → loads `learning.md`
- Task contains "fitness" → loads `fitness.md`
- etc.

### When to Create Context Files

Create a context file when you have:
- **Recurring tasks** with consistent preferences (e.g., meal planning)
- **Long-term tasks** that need progress tracking (e.g., learning projects)
- **Complex tasks** with specific requirements (e.g., workout routines)

### Context File Format

Context files should be Markdown (`.md`) with descriptive names matching keywords in task descriptions.

**Example structure:**

```markdown
# [Task Type] Context

## Preferences/Settings
- Key setting 1
- Key setting 2

## Current State/Progress
- What was done last time
- What's in progress

## Resources/References
- Links, files, or notes

## Next Steps
- What to focus on next

## Notes
- Any other relevant information
- Last updated: [date]
```

## Available Context Files

- `meal_planning.md` - Dietary preferences, recipes, shopping list template
- `learning.md` - Learning goals, progress tracking, resources

## Creating New Context Files

1. Create a new `.md` file in this directory
2. Name it with a keyword that appears in your task descriptions
3. Structure it with sections relevant to your task type
4. Update it manually as needed

## How Workers Use Context

When processing a task, workers:
1. Check task description for matching keywords
2. Load corresponding context file (if exists)
3. Include context in the LLM prompt
4. Use context to provide continuity and personalization

Workers **read-only** - they don't modify context files. You update them manually.

## Best Practices

- ✅ Use clear, descriptive filenames (e.g., `meal_planning.md` not `mp.md`)
- ✅ Include timestamps when updating
- ✅ Keep context concise but comprehensive
- ✅ Update context files after completing related tasks
- ❌ Don't store sensitive information (API keys, passwords)
- ❌ Don't create task-specific contexts for one-off tasks

## Examples

### Meal Planning Task
```
Task: "Create weekly meal planning for next week"
Context file: meal_planning.md
Worker: Uses dietary preferences and recipe rotation
```

### Learning Task
```
Task: "Continue learning LangGraph - focus on memory patterns"
Context file: learning.md
Worker: Knows previous topics, current progress, learning style
```

---

**Last Updated**: 2025-11-13
