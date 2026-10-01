import hashlib, os, re
from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from .auth import admin
from .db import need_db

router = APIRouter()
BOT = re.compile(r"bot|crawl|spider|preview|monitor|headless|curl|python-requests", re.I)
TZ = "Africa/Lagos"


class Track(BaseModel):
    path: str = Field(max_length=300)
    ref: str = Field("", max_length=500)
    host: str = Field("", max_length=200)
    ua: str = Field("", max_length=400)
    ip: str = Field("", max_length=64)
    country: str = Field("", max_length=8)
    region: str = Field("", max_length=80)
    city: str = Field("", max_length=80)


@router.post("/api/analytics/track")
async def track(b: Track, x_track_secret: str = Header(""), db=Depends(need_db)):
    secret = os.getenv("TRACK_SECRET", "")
    if not secret or not compare_digest(x_track_secret, secret):
        raise HTTPException(401, "Unauthorized")
    if BOT.search(b.ua):
        return {"ok": True}
    vid = hashlib.sha256(f"{os.getenv('TRACK_SALT', '')}{b.ip}{b.ua}".encode()).hexdigest()[:16]
    ref = urlparse(b.ref).netloc.replace("www.", "") if b.ref else ""
    if ref and ref == b.host.replace("www.", ""):
        ref = ""
    ua = b.ua.lower()
    device = "Mobile" if re.search(r"mobi|android|iphone", ua) else "Desktop"
    await db.visits.insert_one({
        "ts": datetime.now(timezone.utc), "vid": vid, "path": b.path, "ref": ref, "country": b.country.upper(),
        "place": ", ".join(x for x in [b.city, b.country.upper()] if x), "region": b.region, "device": device,
    })
    return {"ok": True}


@router.get("/api/admin/analytics", dependencies=[Depends(admin)])
async def summary(days: int = 30, db=Depends(need_db)):
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    m = {"ts": {"$gte": since}}

    async def top(field: str, n: int = 10):
        pipe = [{"$match": m}, {"$group": {"_id": f"${field}", "views": {"$sum": 1}, "v": {"$addToSet": "$vid"}}},
                {"$project": {"views": 1, "visitors": {"$size": "$v"}}}, {"$sort": {"views": -1}}, {"$limit": n}]
        return [{"name": d["_id"] or "Unknown / direct", "views": d["views"], "visitors": d["visitors"]} async for d in db.visits.aggregate(pipe)]

    async def bucket(fmt):
        pipe = [{"$match": m}, {"$group": {"_id": fmt, "views": {"$sum": 1}, "v": {"$addToSet": "$vid"}}},
                {"$project": {"views": 1, "visitors": {"$size": "$v"}}}]
        return {d["_id"]: d async for d in db.visits.aggregate(pipe)}

    per_day = await bucket({"$dateToString": {"format": "%Y-%m-%d", "date": "$ts", "timezone": TZ}})
    per_hour = await bucket({"$hour": {"date": "$ts", "timezone": TZ}})
    today = datetime.now(timezone.utc).date()
    daily = []
    for i in range(days - 1, -1, -1):
        k = (today - timedelta(days=i)).isoformat()
        d = per_day.get(k, {})
        daily.append({"day": k, "views": d.get("views", 0), "visitors": d.get("visitors", 0)})
    recent = [{"ts": r["ts"].isoformat() + "Z", "path": r["path"], "place": r.get("place") or "Unknown", "ref": r.get("ref") or "direct", "device": r.get("device", "")}
              async for r in db.visits.find().sort("ts", -1).limit(30)]
    return {
        "views": await db.visits.count_documents(m), "visitors": len(await db.visits.distinct("vid", m)),
        "daily": daily, "hours": [per_hour.get(h, {}).get("views", 0) for h in range(24)],
        "countries": await top("country"), "places": await top("place"), "referrers": await top("ref"),
        "pages": await top("path"), "devices": await top("device", 5), "recent": recent,
    }
