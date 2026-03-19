from .orchestrator import (
    load_queue,
    save_queue,
    get_next_task,
    load_spec,
    build_prompt,
    run_task,
    save_output,
    mark_complete,
)

from .config import (
    QUEUE_PATH,
    OUTPUT_DIR,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

__version__ = "0.1.0"
__author__  = "ESC Software Solutions"