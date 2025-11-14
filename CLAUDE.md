Virtual environment - use uv and the environment is in /Users/abhinav/Desktop/ai_projects/Xponentially/.venv

How to use local llm example can be found in /Users/abhinav/Desktop/ai_projects/ollama-playground/ai-researcher/ai_researcher.py 
It also provides examples of using the web. 

How to structure agents is found in /Users/abhinav/Desktop/ai_projects/learning_data_agents 
Mainly read the L2 and L3 files. 

How to get tasks from Todoist is in /Users/abhinav/Desktop/Macbook_M3/Desktop/python-projects/2024_assistant/Agents/Todoist_Agent

## Git Conventions

### Commit Message Format
Follow the template in `.gitmessage`:
- **Type prefix:** feat, fix, refactor, docs, test, chore, perf, style
- **Subject:** Imperative mood, 50 chars max, no period
- **Body:** Explain why (not how), 72 chars per line
- **Co-authored:** Add `Co-Authored-By: Claude <noreply@anthropic.com>` for Claude commits

Example:
```
feat: add task-loop architecture for intelligent routing

- Redesigned executor to process tasks one at a time
- Added LLM-based routing decisions per task
- Implemented task completion validation
- Each task now goes to appropriate worker based on type

Co-Authored-By: Claude <noreply@anthropic.com>
```

### What to Commit
- **DO commit:** Source code, configs (without secrets), documentation, requirements.txt
- **DON'T commit:** .env files, .venv/, __pycache__/, logs, API keys

### Branching Strategy
- `main` - production-ready code
- `feature/<name>` - new features
- `fix/<name>` - bug fixes
- `refactor/<name>` - code improvements

### Before Committing
1. Verify `.env` is not staged
2. Check no API keys in code
3. Run basic smoke test if applicable
4. Review diff to ensure only intended changes included