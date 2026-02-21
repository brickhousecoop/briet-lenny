"""Book catalog for the BRIET lending demo.

Storage hierarchy (read):
  1. In-memory cache (30 s TTL — fast, avoids repeated network calls)
  2. Vercel Blob  (persistent across deploys, requires BLOB_READ_WRITE_TOKEN)
  3. /tmp/catalog.json  (warm-invocation cache; local-dev writable copy)
  4. catalog.json at project root  (seed data, read-only on Vercel)

Storage hierarchy (write):
  1. Vercel Blob  (primary persistent store when available)
  2. /tmp/catalog.json  (always written for local-dev and warm-cache)
  3. In-memory cache  (updated immediately so the current request sees changes)
"""

import json
import time
from pathlib import Path

from lenny.core import blob

# Deployed seed file (read-only on Vercel)
_CATALOG_SRC = Path(__file__).resolve().parent.parent.parent / "catalog.json"
# Writable copy used at runtime (ephemeral on Vercel)
_CATALOG_TMP = Path("/tmp/catalog.json")

# ---------------------------------------------------------------------------
# In-memory cache (avoids hitting Blob API on every page load)
# ---------------------------------------------------------------------------
_cache: list[dict] | None = None
_cache_time: float = 0
_CACHE_TTL = 30  # seconds


def _load() -> list[dict]:
    """Read catalog using the storage hierarchy described above."""
    global _cache, _cache_time

    # 1. In-memory cache
    if _cache is not None and (time.time() - _cache_time) < _CACHE_TTL:
        return _cache

    # 2. Vercel Blob (persistent across deploys)
    if blob.BLOB_ENABLED:
        data = blob.get("catalog.json")
        if data:
            catalog = json.loads(data)
            _cache = catalog
            _cache_time = time.time()
            return catalog

    # 3. /tmp copy (warm-invocation cache / local dev)
    if _CATALOG_TMP.exists():
        catalog = json.loads(_CATALOG_TMP.read_text())
        _cache = catalog
        _cache_time = time.time()
        return catalog

    # 4. Seed file
    if _CATALOG_SRC.exists():
        return json.loads(_CATALOG_SRC.read_text())

    return []


def _save(catalog: list[dict]) -> None:
    """Write catalog to persistent storage."""
    global _cache, _cache_time

    payload = json.dumps(catalog, indent=2) + "\n"

    # 1. Vercel Blob (survives deploys)
    if blob.BLOB_ENABLED:
        blob.put("catalog.json", payload.encode(), "application/json")

    # 2. /tmp (warm-invocation cache / local dev)
    _CATALOG_TMP.write_text(payload)

    # 3. Update in-memory cache immediately
    _cache = catalog
    _cache_time = time.time()


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
