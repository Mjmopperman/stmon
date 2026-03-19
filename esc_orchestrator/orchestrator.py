import re
import yaml
import requests
from datetime import date
from pathlib import Path

from .config import (
    BASE_DIR,
    QUEUE_PATH,
    OUTPUT_DIR,
    SPEC_BASE_PATH,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    STATUS_PENDING,
    STATUS_DONE,
)


# ─────────────────────────────────────────
# Function 1: load_queue
# ─────────────────────────────────────────
def load_queue(queue_path: Path = QUEUE_PATH) -> dict:
    if not queue_path.exists():
        raise FileNotFoundError(f"Queue file not found: {queue_path}")
    with open(queue_path, "r") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────
# Function 2: save_queue
# ─────────────────────────────────────────
def save_queue(queue: dict, queue_path: Path = QUEUE_PATH) -> None:
    with open(queue_path, "w") as f:
        yaml.dump(
            queue, f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )


# ─────────────────────────────────────────
# Function 3: get_next_task
# ─────────────────────────────────────────
def get_next_task(queue: dict) -> dict | None:
    for task in queue["tasks"]:
        if task["status"] == STATUS_PENDING:
            return task
    return None


# ─────────────────────────────────────────
# Function 4: load_spec
# ─────────────────────────────────────────
def load_spec(task: dict, base_path: Path = SPEC_BASE_PATH) -> dict:
    spec_path = base_path / task["yaml"]
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    with open(spec_path, "r") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────
# Function 5: build_prompt
# ─────────────────────────────────────────
def build_prompt(task: dict, spec: dict) -> str:
    return f"""You are implementing one module of a larger system.

TASK ID: {task["id"]}
INSTRUCTION: {task["prompt"]}

SPECIFICATION:
{yaml.dump(spec, default_flow_style=False, allow_unicode=True, sort_keys=False)}

Rules:
- Implement exactly what the specification describes. Nothing more.
- Do not invent fields, routes, or logic not present in the spec.
- Do not ask clarifying questions. The spec is complete.
- Output only the implementation. No explanation unless the spec requests it.
"""


# ─────────────────────────────────────────
# Function 6: run_task
# ─────────────────────────────────────────
def run_task(
    prompt: str,
    model: str = OLLAMA_MODEL,
    base_url: str = OLLAMA_BASE_URL
) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Model timed out after {OLLAMA_TIMEOUT}s. "
            f"Try increasing OLLAMA_TIMEOUT or use a smaller model."
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Could not reach Ollama at {base_url}. Is it running?"
        )
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama returned an error: {e}")


# ─────────────────────────────────────────
# Function 7: save_output
# ─────────────────────────────────────────
def save_output(
    task: dict,
    output: str,
    output_dir: Path = OUTPUT_DIR
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{task['id']}_"
        f"{task['yaml'].replace('/', '_').replace('.yaml', '')}"
        f".txt"
    )
    file_path = output_dir / filename

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"TASK:   {task['id']}\n")
        f.write(f"SPEC:   {task['yaml']}\n")
        f.write(f"PROMPT: {task['prompt']}\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(output)

    return file_path


# ─────────────────────────────────────────
# Function 8: mark_complete
# ─────────────────────────────────────────
def mark_complete(queue: dict, task: dict, output_file: Path) -> None:
    for t in queue["tasks"]:
        if t["id"] == task["id"]:
            t["status"] = STATUS_DONE
            t["output"] = str(output_file)
            break
    save_queue(queue)

def update_claude_md(
    completed_task: dict,
    next_task: dict | None,
    claude_md_path: Path = BASE_DIR / "CLAUDE.md"
) -> None:

    today = date.today().isoformat()

    next_section = (
        f"- **{next_task['id']}:** `{next_task['yaml']}`\n"
        f"  {next_task['prompt']}"
        if next_task
        else "- All tasks complete."
    )

    update_block = f"""## Session Update

_Last updated: {today}_

### Completed
- **{completed_task['id']}:** `{completed_task['yaml']}`
  Output: `{completed_task.get('output', 'see build/output/')}`

### Up Next
{next_section}
"""

    if not claude_md_path.exists():
        raise FileNotFoundError(f"CLAUDE.md not found at {claude_md_path}")

    content = claude_md_path.read_text(encoding="utf-8")

    if "## Session Update" in content:
        content = re.sub(
            r"## Session Update.*?(?=\n## |\Z)",
            update_block,
            content,
            flags=re.DOTALL
        )
    else:
        content = content.rstrip() + "\n\n" + update_block

    claude_md_path.write_text(content, encoding="utf-8")

# ─────────────────────────────────────────
# Main loop — single task mode
# ─────────────────────────────────────────
def main():
    print("ESC Orchestrator v0.1.0")
    print("─" * 40)

    print("Loading queue...")
    queue = load_queue()

    task = get_next_task(queue)
    if task is None:
        print("All tasks complete. Nothing to do.")
        return

    print(f"\nTask:   {task['id']}")
    print(f"Spec:   {task['yaml']}")
    print(f"Prompt: {task['prompt']}")
    print("─" * 40)

    print("Loading spec...")
    spec = load_spec(task)

    print("Building prompt...")
    prompt = build_prompt(task, spec)

    print("Running model...")
    output = run_task(prompt)

    print("Saving output...")
    output_file = save_output(task, output)

    print("Marking complete...")
    mark_complete(queue, task, output_file)

    print("Updating CLAUDE.md...")
    next_task = get_next_task(queue)
    update_claude_md(task, next_task)

    print(f"\n✓ Done.")
    print(f"  Output: {output_file}")
    print(f"  Run again to process next task.")


if __name__ == "__main__":
    main()