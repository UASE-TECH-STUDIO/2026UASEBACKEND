import logging
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from . import analytics, auth, content
from .auth import ip, limit
from .db import db, need_db
from .seed import seed_posts


log = logging.getLogger("uvicorn.error")


def env(key: str, default: str = "") -> str:
    """Read an env var and strip stray quotes/spaces (some dashboards keep the quotes)."""
    return os.getenv(key, default).strip().strip("\"'")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if db is not None:
        await db.likes.create_index([("slug", 1), ("visitor", 1)], unique=True)
        await db.visits.create_index("ts")
        if os.getenv("SEED_POSTS", "1") == "1" and await db.posts.count_documents({}) == 0:
            await db.posts.insert_many(seed_posts())
    yield


app = FastAPI(title="UASE Tech Studio API", lifespan=lifespan)
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"],
                   allow_origin_regex=os.getenv("ALLOWED_ORIGIN_REGEX") or None)
for r in (auth.router, content.router, analytics.router):
    app.include_router(r)


class Contact(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(min_length=1, max_length=4000)
    website: str = ""  # honeypot


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/contact")
async def contact(body: Contact, req: Request):
    if body.website:
        return {"ok": True}
    limit("contact:" + ip(req), 6, 600)
    saved = sent = False
    if db is not None:  # the database copy is the safety net: you can read it in /admin
        try:
            await db.contacts.insert_one({**body.model_dump(exclude={"website"}), "created": datetime.now(timezone.utc), "read": False})
            saved = True
        except Exception as e:
            log.error("contact: could not save message: %s", e)
    key = env("RESEND_API_KEY")
    if key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}"}, json={
                    "from": env("CONTACT_FROM_EMAIL", "UASE Website <onboarding@resend.dev>"),
                    "to": [env("CONTACT_TO_EMAIL", "uasetechstudio@gmail.com")],
                    "reply_to": body.email, "subject": f"New website message from {body.name}",
                    "text": f"From: {body.name} <{body.email}>\n\n{body.message}"})
            sent = r.status_code < 300
            if not sent:
                log.error("contact: Resend rejected the email: %s %s", r.status_code, r.text[:300])
        except Exception as e:
            log.error("contact: Resend request failed: %s", e)
    if not (saved or sent):
        raise HTTPException(503, "We couldn't receive your message right now. Please use WhatsApp or email.")
    return {"ok": True, "saved": saved, "emailed": sent}
