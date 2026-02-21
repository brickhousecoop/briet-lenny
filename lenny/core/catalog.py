"""Static book catalog for the BRIET lending demo.

In production Lenny, this comes from PostgreSQL.
For the demo, it's a simple in-memory list.
"""

CATALOG = [
    {
        "id": "demo-book-1",
        "title": "Cooking with Curiosity (BRIET Edition)",
        "author": "BRIET Collection",
        "description": (
            "A demonstration title available for lending through "
            "the BRIET Digital Lending platform. Partner library patrons "
            "can borrow this title after authenticating with their library credentials."
        ),
        "format": "PDF",
        "total_copies": 3,
        "filename": "Cooking with Curiosity (BRIET Edition) Interior.pdf",
    },
]


def get_catalog() -> list[dict]:
    """Return the full catalog."""
    return CATALOG


def get_book(book_id: str) -> dict | None:
    """Look up a single book by ID."""
    for book in CATALOG:
        if book["id"] == book_id:
            return book
    return None
