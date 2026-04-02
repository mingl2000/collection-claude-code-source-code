"""Tests for the file-based memory system."""
import pytest
from pathlib import Path

import memory
from memory import (
    MemoryEntry, save_memory, load_index, delete_memory,
    search_memory, get_memory_context, _slugify, _parse_frontmatter,
)


@pytest.fixture(autouse=True)
def redirect_memory_dir(tmp_path, monkeypatch):
    """Redirect MEMORY_DIR and INDEX_FILE to tmp_path for all tests."""
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir()
    monkeypatch.setattr(memory, "MEMORY_DIR", mem_dir)
    monkeypatch.setattr(memory, "INDEX_FILE", mem_dir / "MEMORY.md")


def _make_entry(name="test note", description="a test", type_="user",
                content="hello world"):
    return MemoryEntry(
        name=name, description=description, type=type_,
        content=content, created="2026-04-02",
    )


class TestSaveAndLoad:
    def test_roundtrip(self):
        entry = _make_entry()
        save_memory(entry)
        loaded = load_index()
        assert len(loaded) == 1
        assert loaded[0].name == "test note"
        assert loaded[0].description == "a test"
        assert loaded[0].type == "user"
        assert loaded[0].content == "hello world"

    def test_creates_file_on_disk(self):
        entry = _make_entry()
        save_memory(entry)
        assert Path(entry.file_path).exists()
        text = Path(entry.file_path).read_text()
        assert "hello world" in text

    def test_update_existing(self):
        """Save same name twice: only 1 entry remains with updated content."""
        save_memory(_make_entry(content="version 1"))
        save_memory(_make_entry(content="version 2"))
        loaded = load_index()
        assert len(loaded) == 1
        assert loaded[0].content == "version 2"


class TestDelete:
    def test_delete_removes_file_and_index(self):
        entry = _make_entry()
        save_memory(entry)
        delete_memory("test note")
        assert load_index() == []
        assert not Path(entry.file_path).exists()
        # Index file should exist but be empty
        assert memory.INDEX_FILE.exists()

    def test_delete_nonexistent_no_error(self):
        delete_memory("nonexistent")


class TestSearch:
    def test_search_by_keyword(self):
        save_memory(_make_entry(name="python tips", content="use list comprehension"))
        save_memory(_make_entry(name="rust tips", content="use iterators"))
        results = search_memory("python")
        assert len(results) == 1
        assert results[0].name == "python tips"

    def test_search_case_insensitive(self):
        save_memory(_make_entry(name="Important Note", content="something"))
        results = search_memory("important")
        assert len(results) == 1

    def test_search_in_content(self):
        save_memory(_make_entry(name="misc", content="the quick brown fox"))
        results = search_memory("brown fox")
        assert len(results) == 1


class TestGetMemoryContext:
    def test_returns_index_text(self):
        save_memory(_make_entry(name="my note", description="desc here"))
        ctx = get_memory_context()
        assert "my note" in ctx
        assert "desc here" in ctx

    def test_empty_when_no_memories(self):
        ctx = get_memory_context()
        assert ctx == ""


class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello_world"

    def test_special_chars(self):
        assert _slugify("foo@bar!baz") == "foobarbaz"

    def test_max_length(self):
        assert len(_slugify("a" * 100)) == 60


class TestParseFrontmatter:
    def test_parse(self):
        text = "---\nname: foo\ntype: user\n---\nbody text"
        meta, body = _parse_frontmatter(text)
        assert meta["name"] == "foo"
        assert meta["type"] == "user"
        assert body == "body text"

    def test_no_frontmatter(self):
        meta, body = _parse_frontmatter("just plain text")
        assert meta == {}
        assert body == "just plain text"
