"""Route handlers for the BRIET Digital Lending demo.

Implements: landing page, simulated OAuth, catalog browsing,
borrowing/returning, PDF reading, and user bookshelf.
"""

import os
from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from lenny.core.auth import (
    get_session,
    create_session,
    update_borrowed,
    SESSION_COOKIE,
)
from lenny.core.catalog import get_catalog, get_book

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "lenny" / "templates"
BOOKS_DIR = BASE_DIR / "books"

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

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=book["filename"],
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key=SESSION_COOKIE)
    return response
