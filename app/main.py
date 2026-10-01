import os
from contextlib import asynccontextmanager
import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from . import analytics, auth, content
from .db import db, need_db
from .seed import seed_posts


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
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])
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
async def contact(body: Contact):
    if body.website:
        return {"ok": True}
    if db is not None:
        await db.contacts.insert_one(body.model_dump(exclude={"website"}))
    key, to = os.getenv("RESEND_API_KEY"), os.getenv("CONTACT_TO_EMAIL", "uasetechstudio@gmail.com")
    if key:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}"}, json={
                "from": os.getenv("CONTACT_FROM_EMAIL", "UASE Website <onboarding@resend.dev>"), "to": [to],
                "reply_to": body.email, "subject": f"New website message from {body.name}",
                "text": f"From: {body.name} <{body.email}>\n\n{body.message}"})
        if r.status_code >= 300:
            raise HTTPException(502, "Email delivery failed")
    elif db is None:
        raise HTTPException(503, "No delivery channel configured")
    return {"ok": True}
