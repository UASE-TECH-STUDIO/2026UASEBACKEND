import os
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

_c = AsyncIOMotorClient(os.environ["MONGODB_URI"]) if os.getenv("MONGODB_URI") else None
db = _c[os.getenv("MONGODB_DB", "uase")] if _c is not None else None


def need_db():
    if db is None:
        raise HTTPException(503, "Database not configured")
    return db
