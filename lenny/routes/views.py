"""Route handlers for the BRIET Digital Lending demo.

Implements: landing page, simulated OAuth, catalog browsing,
borrowing/returning, PDF reading, and user bookshelf.
"""

import base64
from pathlib import Path
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from lenny.core.auth import (
    get_session,
    create_session,
    update_borrowed,
    SESSION_COOKIE,
)
from lenny.core.catalog import get_catalog, get_book, update_book

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "lenny" / "templates"
BOOKS_DIR = BASE_DIR / "books"

MAX_COVER_BYTES = 2 * 1024 * 1024  # 2 MB

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _require_login(session: dict | None) -> None:
    """Raise redirect if not logged in."""
    if session is None:
        raise HTTPException(status_code=303, headers={"Location": "/"})


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session = get_session(request)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "session": session,
    })


# ---------------------------------------------------------------------------
# Simulated OAuth flow
# ---------------------------------------------------------------------------

@router.get("/oauth/authorize", response_class=HTMLResponse)
async def oauth_login_form(request: Request, library: str = "Partner Library"):
    """Show the simulated partner library login form."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "library": library,
    })


@router.post("/oauth/authorize")
async def oauth_login_submit(
    request: Request,
    email: str = Form(...),
    card_number: str = Form(...),
    library: str = Form("Partner Library"),
):
    """Process the simulated login. Any credentials are accepted for the demo."""
    token = create_session(email=email, library=library)
    response = RedirectResponse(url="/catalog", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

@router.get("/catalog", response_class=HTMLResponse)
async def catalog(request: Request):
    session = get_session(request)
    if session is None:
        return RedirectResponse(url="/", status_code=303)
    books = get_catalog()
    borrowed_ids = session.get("borrowed", [])
    return templates.TemplateResponse("catalog.html", {
        "request": request,
        "session": session,
        "books": books,
        "borrowed_ids": borrowed_ids,
    })


# ---------------------------------------------------------------------------
# Borrow / Return
# ---------------------------------------------------------------------------

@router.post("/catalog/{book_id}/borrow")
async def borrow_book(request: Request, book_id: str):
    session = get_session(request)
    if session is None:
        return RedirectResponse(url="/", status_code=303)

    book = get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    new_token = update_borrowed(session, book_id, "borrow")
    response = RedirectResponse(url="/shelf", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=new_token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


@router.post("/catalog/{book_id}/return")
async def return_book(request: Request, book_id: str):
    session = get_session(request)
    if session is None:
        return RedirectResponse(url="/", status_code=303)

    new_token = update_borrowed(session, book_id, "return")
    response = RedirectResponse(url="/shelf", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=new_token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


# ---------------------------------------------------------------------------
# Bookshelf (user's borrowed books)
# ---------------------------------------------------------------------------

@router.get("/shelf", response_class=HTMLResponse)
async def shelf(request: Request):
    session = get_session(request)
    if session is None:
        return RedirectResponse(url="/", status_code=303)

    borrowed_ids = session.get("borrowed", [])
    borrowed_books = [get_book(bid) for bid in borrowed_ids if get_book(bid)]
    return templates.TemplateResponse("shelf.html", {
        "request": request,
        "session": session,
        "books": borrowed_books,
    })


# ---------------------------------------------------------------------------
# Reader (serves the book for reading)
# ---------------------------------------------------------------------------

@router.get("/catalog/{book_id}/read", response_class=HTMLResponse)
async def read_book(request: Request, book_id: str):
    session = get_session(request)
    if session is None:
        return RedirectResponse(url="/", status_code=303)

    borrowed_ids = session.get("borrowed", [])
    if book_id not in borrowed_ids:
        return RedirectResponse(url="/catalog", status_code=303)

    book = get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    return templates.TemplateResponse("reader.html", {
        "request": request,
        "session": session,
        "book": book,
    })


@router.get("/books/{book_id}/download")
async def download_book(request: Request, book_id: str):
    """Serve the book file. Requires authentication and an active loan."""
    session = get_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Login required")

    borrowed_ids = session.get("borrowed", [])
    if book_id not in borrowed_ids:
        raise HTTPException(status_code=403, detail="You must borrow this book first")

    book = get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    file_path = BOOKS_DIR / book["filename"]
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Book file not yet uploaded. Add a PDF to the books/ directory.",
        )

    data = file_path.read_bytes()
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------------------------------------------------------------------------
# Admin — catalog metadata editor
# ---------------------------------------------------------------------------

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, saved: bool = False):
    books = get_catalog()
    session = get_session(request)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "session": session,
        "books": books,
        "saved": saved,
    })


@router.get("/covers/{book_id}")
async def serve_cover(book_id: str):
    """Serve a cover image stored as base64 in catalog.json."""
    book = get_book(book_id)
    if not book or not book.get("cover_data"):
        raise HTTPException(status_code=404, detail="No cover image")
    data = base64.b64decode(book["cover_data"])
    content_type = book.get("cover_type", "image/jpeg")
    return Response(content=data, media_type=content_type)


@router.post("/admin/catalog/{book_id}")
async def admin_update_book(
    request: Request,
    book_id: str,
    title: str = Form(""),
    author: str = Form(""),
    publisher: str = Form(""),
    year: str = Form(""),
    description: str = Form(""),
    cover_file: UploadFile | None = File(None),
):
    """Save metadata edits and optional cover image upload."""
    updates = {
        "title": title,
        "author": author,
        "publisher": publisher,
        "year": year,
        "description": description,
    }

    # If a new cover was uploaded, base64-encode and store in catalog
    if cover_file and cover_file.filename:
        content = await cover_file.read()
        if content:
            if len(content) > MAX_COVER_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail="Cover image must be under 2 MB.",
                )
            updates["cover_data"] = base64.b64encode(content).decode("ascii")
            updates["cover_type"] = cover_file.content_type or "image/jpeg"

    update_book(book_id, updates)
    return RedirectResponse(url="/admin?saved=1", status_code=303)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key=SESSION_COOKIE)
    return response
