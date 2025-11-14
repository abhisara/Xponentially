"""
Configuration file for Todoist API and other credentials.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Todoist API Token
# You can set this in a .env file as: TODOIST_API_TOKEN=your_token_here
# Or set it directly here (not recommended for production)
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN", "")

if not TODOIST_API_TOKEN:
    raise ValueError(
        "TODOIST_API_TOKEN not found. Please set it in a .env file or environment variable."
    )

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")

# Cloud LLM Configuration
# LLM_PROVIDER options: "anthropic", "openai", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model names for each provider
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Output Configuration
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
