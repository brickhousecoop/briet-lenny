"""Book catalog for the BRIET lending demo.

Reads seed data from catalog.json at the project root.  Writes go to
/tmp/catalog.json so admin edits work on Vercel (where the deployed
code directory is read-only).  The /tmp copy is preferred for reads
once it exists; data there survives across warm invocations but is
lost on cold starts.
"""

import json
from pathlib import Path

# Deployed seed file (read-only on Vercel)
_CATALOG_SRC = Path(__file__).resolve().parent.parent.parent / "catalog.json"
# Writable copy used at runtime
_CATALOG_TMP = Path("/tmp/catalog.json")


def _load() -> list[dict]:
    """Read catalog, preferring the /tmp copy when available."""
    if _CATALOG_TMP.exists():
        return json.loads(_CATALOG_TMP.read_text())
    if _CATALOG_SRC.exists():
        return json.loads(_CATALOG_SRC.read_text())
    return []


def _save(catalog: list[dict]) -> None:
    """Write catalog to /tmp (always writable, even on Vercel)."""
    _CATALOG_TMP.write_text(json.dumps(catalog, indent=2) + "\n")


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
