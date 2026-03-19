import shutil
from pathlib import Path

from .config import (
    BASE_DIR,
    QUEUE_PATH,
    OUTPUT_DIR,
    SPEC_BASE_PATH,
    STATUS_DONE,
    STATUS_DEPLOYED,
    STATUS_SKIPPED,
)

from .orchestrator import load_queue, save_queue, load_spec

def load_deployable_queue(queue_path: Path = QUEUE_PATH) -> list:
    queue = load_queue(queue_path)
    return [
        task for task in queue["tasks"]
        if task["status"] == STATUS_DONE
    ]


def read_output(task: dict) -> str:
    output_path = Path(task["output"])
    if not output_path.exists():
        raise FileNotFoundError(
            f"Output file not found: {output_path}\n"
            f"Has the orchestrator run for task {task['id']}?"
        )
    return output_path.read_text(encoding="utf-8")

def extract_code(raw_output: str) -> str:
    separator = "=" * 60
    if separator in raw_output:
        code = raw_output.split(separator, 1)[1].strip()
    else:
        code = raw_output.strip()
    
    # Strip markdown code fences if model added them
    lines = code.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    
    return "\n".join(lines).strip()

def load_output_file(task: dict) -> Path:
    spec = load_spec(task)
    
    if "output_file" not in spec:
        raise KeyError(
            f"Spec file {task['yaml']} is missing the 'output_file' field.\n"
            f"Add 'output_file: path/to/destination' to the spec."
        )
    
    output_file = BASE_DIR / spec["output_file"]
    return output_file

def show_preview(task: dict, code: str, destination: Path) -> None:
    width = 60
    print("\n" + "═" * width)
    print(f"  TASK:   {task['id']}")
    print(f"  SPEC:   {task['yaml']}")
    print(f"  DEST:   {destination}")
    print("═" * width)
    print()

    lines = code.splitlines()
    if len(lines) > 40:
        for line in lines[:20]:
            print(line)
        print(f"\n  ... [{len(lines) - 40} lines hidden] ...\n")
        for line in lines[-20:]:
            print(line)
    else:
        print(code)

    print()
    print("═" * width)

def get_decision() -> str:
    print("  [A] Accept — deploy to destination")
    print("  [E] Edit   — open output file first")
    print("  [S] Skip   — leave for later")
    print("  [Q] Quit   — stop deployer")
    print()

    while True:
        choice = input("  Decision: ").strip().upper()
        if choice in ("A", "E", "S", "Q"):
            return choice
        print(f"  Invalid choice '{choice}'. Enter A, E, S or Q.")

def deploy_file(code: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    if destination.exists():
        backup_path = destination.with_suffix(
            destination.suffix + ".bak"
        )
        shutil.copy2(destination, backup_path)
        print(f"  Backup: {backup_path}")
    
    destination.write_text(code, encoding="utf-8")
    print(f"  Deployed: {destination}")

def mark_deployed(task: dict, queue_path: Path = QUEUE_PATH) -> None:
    queue = load_queue(queue_path)
    
    for t in queue["tasks"]:
        if t["id"] == task["id"]:
            t["status"] = STATUS_DEPLOYED
            break
    
    save_queue(queue)
    print(f"  Status: {task['id']} marked as deployed")


def mark_skipped(task: dict, queue_path: Path = QUEUE_PATH) -> None:
    queue = load_queue(queue_path)
    
    for t in queue["tasks"]:
        if t["id"] == task["id"]:
            t["status"] = STATUS_SKIPPED
            break
    
    save_queue(queue)
    print(f"  Status: {task['id']} marked as skipped")

def main():
    print("\nESC Deployer v0.1.0")
    print("═" * 60)

    tasks = load_deployable_queue()

    if not tasks:
        print("\n  No tasks ready for deployment.")
        print("  Run the orchestrator first to generate output files.")
        return

    print(f"\n  {len(tasks)} task(s) ready for deployment.\n")

    for task in tasks:
        try:
            raw_output  = read_output(task)
            code        = extract_code(raw_output)
            destination = load_output_file(task)

        except (FileNotFoundError, KeyError) as e:
            print(f"\n  ERROR: {e}")
            print(f"  Skipping {task['id']}.\n")
            continue

        while True:
            show_preview(task, code, destination)
            decision = get_decision()

            if decision == "Q":
                print("\n  Deployer stopped. Progress saved.")
                return

            elif decision == "S":
                mark_skipped(task)
                print(f"  Skipped.\n")
                break

            elif decision == "E":
                print(f"\n  Opening output file for editing...")
                import subprocess
                subprocess.run(
                    ["notepad", str(Path(task["output"]))],
                    check=False
                )
                raw_output  = read_output(task)
                code        = extract_code(raw_output)
                print("\n  File reloaded. Showing updated preview...\n")
                continue

            elif decision == "A":
                deploy_file(code, destination)
                mark_deployed(task)
                print(f"  ✓ Deployed.\n")
                break

    print("═" * 60)
    print("  All tasks processed.")
    print("  Run the orchestrator for new tasks.\n")
