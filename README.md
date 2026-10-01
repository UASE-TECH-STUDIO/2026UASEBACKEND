# 2026UASEBACKEND

FastAPI service for the UASE Tech Studio website (contact form).

## Environment variables (Render dashboard, or .env locally)
| Name | Value |
|---|---|
| MONGODB_URI | MongoDB Atlas connection string |
| ALLOWED_ORIGINS | Your Vercel domain(s), comma separated, e.g. https://uase.tech,https://YOUR-APP.vercel.app |
| ADMIN_PASSWORD | Long password for /admin |
| JWT_SECRET | Long random string (32+ characters) |
| TRACK_SECRET | Random string, identical to TRACK_SECRET on Vercel |
| TRACK_SALT | Any random string (hashes visitor IPs; raw IPs are never stored) |
| CLOUDINARY_URL | cloudinary://API_KEY:API_SECRET@CLOUD_NAME (admin uploads) |
| RESEND_API_KEY | Optional: emails contact-form messages to you |

## Run locally (PowerShell)
    python -m venv .venv; .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    uvicorn app.main:app --reload

## Deploy on Render (Web Service)
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables: see `.env.example` (set ALLOWED_ORIGINS to your Vercel domain)
- Health check path: `/health`

## Admin, blog, resources and analytics
- Set `ADMIN_PASSWORD`, `JWT_SECRET`, `TRACK_SECRET`, `TRACK_SALT`, `MONGODB_URI` and `CLOUDINARY_URL` on Render (see `.env.example`).
- Six starter blog posts are inserted automatically the first time the database is empty (set `SEED_POSTS=0` to turn this off).
- Log in at `/admin` on the website. Visits are recorded through the website's `/api/track` route, which reads Vercel's location headers.

## Render settings (must be Python, not Rust/Node)
Language: **Python 3** · Build: `pip install -r requirements.txt` · Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` · Health check: `/health`.
`render.yaml` in this repo holds the same settings (New → Blueprint). `ALLOWED_ORIGIN_REGEX` lets Vercel preview URLs call the API.
