from pathlib import Path

# Paths
BASE_DIR        = Path(__file__).parent.parent
QUEUE_PATH      = BASE_DIR / "build" / "queue.yaml"
OUTPUT_DIR      = BASE_DIR / "build" / "output"
SPEC_BASE_PATH  = BASE_DIR

# Ollama settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "nemotron-3-nano:4b"
OLLAMA_TIMEOUT  = 120

# Queue statuses
STATUS_PENDING  = "pending"
STATUS_DONE     = "done"
STATUS_SKIPPED  = "skipped"