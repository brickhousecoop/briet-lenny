# BRIET Digital Lending

A demonstration deployment of [Lenny](https://github.com/ArchiveLabs/lenny) — the open source Library-in-a-Box — adapted for Vercel.

**Live demo:** https://lending-briet.vercel.app/

## What This Is

This is a self-contained demo of Lenny's core lending workflow, deployed as a Vercel serverless function. It demonstrates:

- **OAuth simulation** — How a partner library's patrons authenticate to borrow books
- **Catalog browsing** — Viewing available titles
- **Borrowing and returning** — The full loan lifecycle
- **In-browser reading** — Embedded PDF viewer for borrowed books

## Architecture

| Component | Production Lenny | This Demo |
|-----------|-----------------|-----------|
| Web framework | FastAPI | FastAPI (same) |
| Database | PostgreSQL | Signed cookies (JWT-like) |
| File storage | MinIO (S3) | Static files |
| Authentication | OAuth / OTP | Simulated OAuth |
| Deployment | Docker Compose | Vercel serverless |

Session state (login, borrowed books) is stored in `itsdangerous`-signed cookies. No external database or storage service is required.

## Project Structure

```
lending_BRIET/
├── api/index.py              # Vercel serverless entry point
├── lenny/
│   ├── app.py                # FastAPI application
│   ├── core/
│   │   ├── auth.py           # Session management (signed cookies)
│   │   └── catalog.py        # Static book catalog
│   ├── routes/
│   │   └── views.py          # All route handlers
│   └── templates/            # Jinja2 HTML templates
├── public/static/style.css   # Stylesheet
├── books/                    # Place demo PDF here as demo.pdf
├── requirements.txt          # Python dependencies
└── vercel.json               # Vercel routing config
```

## Adding a Demo Book

Place a PDF file in the `books/` directory named `demo.pdf`:

```
books/demo.pdf
```

The catalog entry in `lenny/core/catalog.py` can be edited to update the title, author, and description.

## Local Development

```bash
pip install -r requirements.txt
uvicorn lenny.app:app --reload
```

Then open http://localhost:8000
