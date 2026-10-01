import os, time
from collections import defaultdict
from hmac import compare_digest
import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()
_hits: dict = defaultdict(list)


def limit(key: str, n: int, secs: int):
    t = time.time()
    h = [x for x in _hits[key] if t - x < secs]
    if len(h) >= n:
        raise HTTPException(429, "Too many attempts, please try again later")
    _hits[key] = h + [t]


def ip(req: Request) -> str:
    return req.headers.get("x-forwarded-for", "").split(",")[0].strip() or (req.client.host if req.client else "?")


class Login(BaseModel):
    password: str


@router.post("/api/admin/login")
async def login(b: Login, req: Request):
    pw, secret = os.getenv("ADMIN_PASSWORD", ""), os.getenv("JWT_SECRET", "")
    if not pw or not secret:
        raise HTTPException(503, "Admin not configured")
    limit("login:" + ip(req), 5, 900)
    if not compare_digest(b.password.encode(), pw.encode()):
        raise HTTPException(401, "Wrong password")
    return {"token": jwt.encode({"sub": "admin", "exp": int(time.time()) + 8 * 3600}, secret, algorithm="HS256")}


def admin(authorization: str = Header("")):
    secret = os.getenv("JWT_SECRET", "")
    try:
        if not secret:
            raise ValueError
        jwt.decode(authorization.removeprefix("Bearer "), secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Unauthorized")
