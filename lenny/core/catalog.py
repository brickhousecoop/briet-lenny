"""Book catalog for the BRIET lending demo.

Reads from catalog.json at the project root. The admin form writes
back to the same file so changes persist across deploys.
"""

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "catalog.json"


def _load() -> list[dict]:
    """Read catalog from JSON file."""
    if CATALOG_PATH.exists():
        return json.loads(CATALOG_PATH.read_text())
    return []


def _save(catalog: list[dict]) -> None:
    """Write catalog back to JSON file."""
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")


def get_catalog() -> list[dict]:
    """Return the full catalog."""
    return _load()


def get_book(book_id: str) -> dict | None:
    """Look up a single book by ID."""
    for book in _load():
        if book["id"] == book_id:
            return book
    return None


def update_book(book_id: str, data: dict) -> dict | None:
    """Update a book's metadata and save to disk."""
    catalog = _load()
    for book in catalog:
        if book["id"] == book_id:
            book.update(data)
            _save(catalog)
            return book
    return None
