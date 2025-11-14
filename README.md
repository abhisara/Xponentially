# Xponentially - AI-Powered Task Processor

An intelligent task processing system that fetches your Todoist tasks and processes them using a Planner-Executor-Worker architecture with local LLMs via Ollama.

## Architecture

This system implements **Workflow A** - Individual Task Processing:

```
PLANNER → EXECUTOR → WORKERS (specialized processors) → MARKDOWN REPORT
```

### Components:

- **Planner**: Creates execution plan for processing tasks
- **Executor**: Routes tasks to appropriate specialized workers
- **Workers**:
  - `todoist_fetcher`: Fetches today's tasks from Todoist API
  - `task_classifier`: Classifies tasks into types (research/planning/short/learning/abstract)
  - `research_processor`: Processes research tasks
  - `next_action_processor`: Suggests next actions for short tasks
  - `markdown_writer`: Generates formatted markdown report

## Setup

### Prerequisites

1. **Python 3.10+**
2. **Ollama** installed and running locally
   - Install from: https://ollama.ai
   - Pull a model: `ollama pull llama3.2`
3. **Todoist Account** with API access

### Installation

1. **Activate virtual environment**:
   ```bash
   cd /Users/abhinav/Desktop/ai_projects/Xponentially
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Todoist API token:
   ```
   TODOIST_API_TOKEN=your_token_here
   ```

   Get your token from: https://todoist.com/app/settings/integrations/developer

4. **Verify Ollama is running**:
   ```bash
   ollama list  # Should show available models
   ```

## Usage

### Run the Streamlit App

```bash
streamlit run app.py
```

This will open a web interface where you can:
- Click "Process Tasks" to start the workflow
- View real-time progress as tasks are processed
- See the message history from each worker
- Download the generated markdown report

### Output

Processed task reports are saved to the `output/` directory as markdown files with timestamps.

## Project Structure

```
Xponentially/
├── config/
│   ├── config.py           # Configuration and credentials
│   └── ollama_setup.py     # Ollama LLM initialization
├── helpers/
│   ├── state.py            # State management
│   ├── planner.py          # Planner node
│   ├── executor.py         # Executor node
│   └── graph.py            # LangGraph workflow
├── workers/
│   ├── todoist_fetcher.py
│   ├── task_classifier.py
│   ├── research_processor.py
│   ├── next_action_processor.py
│   └── markdown_writer.py
├── prompts/
│   ├── agent_descriptions.py  # Worker metadata
│   └── templates.py           # Prompt templates
├── output/                 # Generated reports
├── app.py                  # Streamlit UI
└── requirements.txt
```

## How It Works

1. **Fetch**: Retrieves today's tasks from Todoist (tasks due today or overdue)
2. **Classify**: Uses Ollama to classify each task into a type
3. **Process**: Routes each task to specialized processor based on type
4. **Report**: Generates comprehensive markdown report with all results

## Extending the System

### Add New Task Types

1. Add processor in `workers/` directory
2. Add description in `prompts/agent_descriptions.py`
3. Add prompt template in `prompts/templates.py`
4. Register in `helpers/graph.py`
5. Add to enabled_agents list

### Current Task Types

- **research**: Tasks requiring information gathering
- **planning**: Tasks needing structured planning
- **short**: Simple tasks needing next action
- **learning**: Educational tasks
- **abstract**: Conceptual/model-building tasks

## Troubleshooting

### Ollama Connection Issues
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama if needed
ollama serve
```

### Todoist API Issues
- Verify your API token is correct
- Check you have tasks due today
- Ensure tasks have due dates set

### LangChain/LangGraph Issues
- Ensure all dependencies are installed
- Check Python version is 3.10+

## Future Enhancements

- **Workflow B**: Batch task analysis (batching, sequencing, visualization)
- Web search integration for research tasks
- Planning methodology framework
- Learning curriculum builder
- Abstract model builder with question generation
- Task dependency tracking
- Integration with note-taking systems

## License

MIT
