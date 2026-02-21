"""Vercel Blob Storage integration for persistent catalog data.

Uses the Vercel Blob REST API so that admin edits (metadata, cover
images) survive across deployments.  Falls back gracefully when no
BLOB_READ_WRITE_TOKEN is configured (e.g. local development).

No extra pip dependencies — uses stdlib urllib only.
"""

import json
import logging
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
_API = "https://blob.vercel-storage.com"

BLOB_ENABLED = bool(_TOKEN)


def _headers(**extra: str) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {_TOKEN}",
        "x-api-version": "7",
    }
    h.update(extra)
    return h


def put(pathname: str, data: bytes, content_type: str = "application/json") -> str | None:
    """Upload *data* to Vercel Blob at *pathname*.

    Uses ``x-add-random-suffix: 0`` so the same pathname is over-
    written on each save (no accumulation of old versions).

    Returns the blob download URL on success, or ``None`` on failure.
    """
    if not BLOB_ENABLED:
        return None
    try:
        req = Request(
            f"{_API}/{pathname}",
            data=data,
            method="PUT",
            headers=_headers(**{
                "x-content-type": content_type,
                "x-add-random-suffix": "0",
            }),
        )
        resp = urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("url")
    except (URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Blob PUT failed for %s: %s", pathname, exc)
        return None


def get(pathname: str) -> bytes | None:
    """Download the blob stored at *pathname*.

    Lists blobs matching the pathname prefix and downloads the first
    match.  Returns raw bytes on success or ``None`` on failure.
    """
    if not BLOB_ENABLED:
        return None
    try:
        from urllib.parse import quote
        req = Request(
            f"{_API}?prefix={quote(pathname, safe='')}&limit=1",
            headers=_headers(),
        )
        resp = urlopen(req, timeout=10)
        listing = json.loads(resp.read())
        blobs = listing.get("blobs", [])
        if not blobs:
            return None

        blob_url = blobs[0]["url"]
        resp2 = urlopen(Request(blob_url), timeout=10)
        return resp2.read()
    except (URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Blob GET failed for %s: %s", pathname, exc)
        return None
