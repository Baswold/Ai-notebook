"""Utility helpers for lightweight per-agent memory persistence.

Memories are stored as markdown files under the workspace `memories/` folder
so that agents can explicitly read and append notes they want to persist
across fresh contexts.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


# Canonical filenames for each agent persona
MEMORY_FILES = {
    "implementer": "implementer_memories.md",
    "reviewer": "reviewer_memories.md",
    "testing": "testing_reviewer_memories.md",
    "testing_reviewer": "testing_reviewer_memories.md",
    "tester": "testing_reviewer_memories.md",
}


def _normalize_agent(agent: str | None) -> str:
    if not agent:
        return "implementer"

    key = agent.strip().lower().replace(" ", "_")

    if key in MEMORY_FILES:
        return key

    if "test" in key:
        return "testing"
    if "review" in key:
        return "reviewer"

    return "implementer"


def get_memory_path(workspace: Path, agent: str | None, ensure_dir: bool = True) -> Path:
    """Return the path to the memory file for the given agent persona."""
    normalized = _normalize_agent(agent)
    filename = MEMORY_FILES.get(normalized, MEMORY_FILES["implementer"])

    memory_dir = workspace / "memories"
    if ensure_dir:
        memory_dir.mkdir(parents=True, exist_ok=True)
        _ensure_gitignore(workspace)

    return memory_dir / filename


def read_memory(workspace: Path, agent: str | None) -> str:
    """Read the saved memory for an agent, if it exists."""
    path = get_memory_path(workspace, agent, ensure_dir=False)
    if not path.exists():
        return ""
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def append_memory(workspace: Path, agent: str | None, content: str) -> Path:
    """Append a timestamped memory entry and return the file path."""
    if not content or not content.strip():
        raise ValueError("Memory content cannot be empty")

    path = get_memory_path(workspace, agent, ensure_dir=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"## {timestamp}\n{content.strip()}\n\n"

    with path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return path


def _ensure_gitignore(workspace: Path) -> None:
    """Ensure memories are excluded from version control."""
    gitignore = workspace / ".gitignore"
    entry = "memories/"

    try:
        if gitignore.exists():
            lines = gitignore.read_text().splitlines()
            if any(line.strip() == entry for line in lines):
                return
        else:
            lines = []

        lines.append(entry)
        gitignore.write_text("\n".join(lines) + "\n")
    except Exception:
        # Non-fatal; best-effort to avoid committing memory files
        pass
