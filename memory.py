"""File-based memory system for nano claude.

Memories stored as markdown files with YAML frontmatter
in ~/.nano_claude/memory/.
"""
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryEntry:
    """A single memory entry.

    Attributes:
        name: human-readable name
        description: short description
        type: "user" | "feedback" | "project" | "reference"
        content: body text
        file_path: path to the .md file on disk
        created: date string, e.g. "2026-04-02"
    """
    name: str
    description: str
    type: str
    content: str
    file_path: str = ""
    created: str = ""


MEMORY_DIR = Path.home() / ".nano_claude" / "memory"
INDEX_FILE = MEMORY_DIR / "MEMORY.md"


def _slugify(name: str) -> str:
    """Convert name to filesystem-safe slug.

    Lowercase, spaces to underscores, strip special chars, max 60 chars.
    """
    s = name.lower().strip()
    s = s.replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s[:60]


def _parse_frontmatter(text: str):
    """Parse ---\\nkey: value\\n---\\nbody format.

    Returns:
        (dict, body_str) where dict has frontmatter keys.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    body = parts[2].strip()
    return meta, body


def save_memory(entry: MemoryEntry) -> None:
    """Write/update memory file and rewrite index.

    If a memory with the same name already exists, overwrite it.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(entry.name)
    fp = MEMORY_DIR / f"{slug}.md"
    content = (
        f"---\n"
        f"name: {entry.name}\n"
        f"description: {entry.description}\n"
        f"type: {entry.type}\n"
        f"created: {entry.created}\n"
        f"---\n"
        f"{entry.content}\n"
    )
    fp.write_text(content)
    entry.file_path = str(fp)
    _rewrite_index()


def _rewrite_index() -> None:
    """Rebuild MEMORY.md from all .md files in the memory dir."""
    entries = load_index()
    lines = [f"- [{e.name}]({Path(e.file_path).name}) — {e.description}" for e in entries]
    INDEX_FILE.write_text("\n".join(lines) + ("\n" if lines else ""))


def load_index() -> list:
    """Scan all .md files (except MEMORY.md), parse frontmatter, return entries.

    Returns:
        list[MemoryEntry]
    """
    if not MEMORY_DIR.exists():
        return []
    entries = []
    for fp in sorted(MEMORY_DIR.glob("*.md")):
        if fp.name == "MEMORY.md":
            continue
        try:
            text = fp.read_text()
        except Exception:
            continue
        meta, body = _parse_frontmatter(text)
        entries.append(MemoryEntry(
            name=meta.get("name", fp.stem),
            description=meta.get("description", ""),
            type=meta.get("type", "user"),
            content=body,
            file_path=str(fp),
            created=meta.get("created", ""),
        ))
    return entries


def delete_memory(name: str) -> None:
    """Remove memory file and update index. No error if not found."""
    slug = _slugify(name)
    fp = MEMORY_DIR / f"{slug}.md"
    if fp.exists():
        fp.unlink()
    _rewrite_index()


def search_memory(query: str) -> list:
    """Case-insensitive keyword match on name+description+content.

    Returns:
        list[MemoryEntry] matching the query.
    """
    q = query.lower()
    results = []
    for e in load_index():
        haystack = f"{e.name} {e.description} {e.content}".lower()
        if q in haystack:
            results.append(e)
    return results


def get_memory_context() -> str:
    """Return MEMORY.md content for system prompt injection.

    Returns empty string if no memories exist.
    """
    if not INDEX_FILE.exists():
        return ""
    text = INDEX_FILE.read_text().strip()
    return text if text else ""
