import os, re
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .auth import admin, ip, limit
from .db import need_db

router = APIRouter()
A = [Depends(admin)]
MAX = 25 * 1024 * 1024
now = lambda: datetime.now(timezone.utc)


def oid(v: str):
    try:
        return ObjectId(v)
    except InvalidId:
        raise HTTPException(404, "Not found")


def ser(d):
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat() + ("" if v.tzinfo else "Z")
    return d


def slugify(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:80] or "post"


class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    excerpt: str = Field("", max_length=400)
    content: str = Field("", max_length=60000)
    cover: str = Field("", max_length=500)
    tags: list[str] = []
    published: bool = True


class CommentIn(BaseModel):
    name: str = Field("", max_length=40)
    message: str = Field(min_length=1, max_length=1000)
    website: str = ""  # honeypot


class LikeIn(BaseModel):
    visitor: str = Field(min_length=8, max_length=64)


async def _counts(db, slugs):
    grp = [{"$match": {"slug": {"$in": slugs}}}, {"$group": {"_id": "$slug", "n": {"$sum": 1}}}]
    likes = {d["_id"]: d["n"] async for d in db.likes.aggregate(grp)}
    coms = {d["_id"]: d["n"] async for d in db.comments.aggregate(grp)}
    return likes, coms


# ---------- public ----------
@router.get("/api/posts")
async def posts(db=Depends(need_db)):
    ps = [ser(p) async for p in db.posts.find({"published": True}, {"content": 0}).sort("created", -1).limit(100)]
    likes, coms = await _counts(db, [p["slug"] for p in ps])
    for p in ps:
        p["likes"], p["comments"] = likes.get(p["slug"], 0), coms.get(p["slug"], 0)
    return ps


@router.get("/api/posts/{slug}")
async def post(slug: str, db=Depends(need_db)):
    p = await db.posts.find_one({"slug": slug, "published": True})
    if not p:
        raise HTTPException(404, "Not found")
    p = ser(p)
    likes, _ = await _counts(db, [slug])
    p["likes"] = likes.get(slug, 0)
    p["comment_list"] = [
        {"name": c["name"], "message": c["message"], "created": ser(c)["created"]}
        async for c in db.comments.find({"slug": slug}).sort("created", -1).limit(200)
    ]
    return p


@router.post("/api/posts/{slug}/comments")
async def comment(slug: str, b: CommentIn, req: Request, db=Depends(need_db)):
    if b.website:
        return {"name": "Ghost", "message": b.message, "created": now().isoformat()}
    limit("c:" + ip(req), 5, 600)
    if not await db.posts.find_one({"slug": slug, "published": True}, {"_id": 1}):
        raise HTTPException(404, "Not found")
    d = {"slug": slug, "name": b.name.strip() or "Ghost", "message": b.message.strip(), "created": now()}
    await db.comments.insert_one(dict(d))
    return {"name": d["name"], "message": d["message"], "created": d["created"].isoformat()}


@router.post("/api/posts/{slug}/like")
async def like(slug: str, b: LikeIn, req: Request, db=Depends(need_db)):
    limit("l:" + ip(req), 60, 600)
    key = {"slug": slug, "visitor": b.visitor}
    if await db.likes.find_one(key):
        await db.likes.delete_one(key)
        liked = False
    else:
        try:
            await db.likes.insert_one(dict(key))
        except Exception:
            pass
        liked = True
    return {"liked": liked, "likes": await db.likes.count_documents({"slug": slug})}


@router.get("/api/resources")
async def resources(db=Depends(need_db)):
    return [ser(r) async for r in db.resources.find().sort("created", -1)]


@router.get("/api/resources/{rid}/download")
async def download(rid: str, db=Depends(need_db)):
    r = await db.resources.find_one_and_update({"_id": oid(rid)}, {"$inc": {"downloads": 1}})
    if not r:
        raise HTTPException(404, "Not found")
    return RedirectResponse(r["url"])


# ---------- admin ----------
async def _upload(file: UploadFile, folder: str, kind: str):
    if not os.getenv("CLOUDINARY_URL"):
        raise HTTPException(503, "File storage not configured (set CLOUDINARY_URL)")
    if (file.size or 0) > MAX:
        raise HTTPException(413, "File too large (max 25MB)")
    import cloudinary.uploader as up
    r = await run_in_threadpool(lambda: up.upload(file.file, folder=folder, resource_type=kind, use_filename=True, unique_filename=True))
    return r["secure_url"], r.get("bytes", 0)


@router.get("/api/admin/posts", dependencies=A)
async def a_posts(db=Depends(need_db)):
    return [ser(p) async for p in db.posts.find().sort("created", -1)]


@router.post("/api/admin/posts", dependencies=A)
async def a_post_new(b: PostIn, db=Depends(need_db)):
    base = slugify(b.title)
    slug, i = base, 2
    while await db.posts.find_one({"slug": slug}, {"_id": 1}):
        slug, i = f"{base}-{i}", i + 1
    d = {**b.model_dump(), "slug": slug, "created": now(), "updated": now()}
    r = await db.posts.insert_one(d)
    return {"id": str(r.inserted_id), "slug": slug}


@router.put("/api/admin/posts/{pid}", dependencies=A)
async def a_post_edit(pid: str, b: PostIn, db=Depends(need_db)):
    r = await db.posts.update_one({"_id": oid(pid)}, {"$set": {**b.model_dump(), "updated": now()}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.delete("/api/admin/posts/{pid}", dependencies=A)
async def a_post_del(pid: str, db=Depends(need_db)):
    p = await db.posts.find_one_and_delete({"_id": oid(pid)})
    if p:
        await db.comments.delete_many({"slug": p["slug"]})
        await db.likes.delete_many({"slug": p["slug"]})
    return {"ok": True}


@router.post("/api/admin/upload", dependencies=A)
async def a_upload(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "Images only")
    url, _ = await _upload(file, "uase/posts", "image")
    return {"url": url}


@router.post("/api/admin/resources", dependencies=A)
async def a_res_new(title: str = Form(..., max_length=160), description: str = Form("", max_length=600),
                    category: str = Form("general", max_length=40), file: UploadFile = File(...), db=Depends(need_db)):
    url, size = await _upload(file, "uase/resources", "auto")
    d = {"title": title, "description": description, "category": category, "url": url,
         "filename": file.filename, "size": size, "downloads": 0, "created": now()}
    r = await db.resources.insert_one(dict(d))
    return {"id": str(r.inserted_id)}


@router.delete("/api/admin/resources/{rid}", dependencies=A)
async def a_res_del(rid: str, db=Depends(need_db)):
    await db.resources.delete_one({"_id": oid(rid)})
    return {"ok": True}


@router.get("/api/admin/comments", dependencies=A)
async def a_comments(db=Depends(need_db)):
    return [ser(c) async for c in db.comments.find().sort("created", -1).limit(100)]


@router.delete("/api/admin/comments/{cid}", dependencies=A)
async def a_comment_del(cid: str, db=Depends(need_db)):
    await db.comments.delete_one({"_id": oid(cid)})
    return {"ok": True}


@router.get("/api/admin/messages", dependencies=A)
async def a_messages(db=Depends(need_db)):
    return [ser(m) async for m in db.contacts.find().sort("created", -1).limit(200)]


@router.delete("/api/admin/messages/{mid}", dependencies=A)
async def a_message_del(mid: str, db=Depends(need_db)):
    await db.contacts.delete_one({"_id": oid(mid)})
    return {"ok": True}
