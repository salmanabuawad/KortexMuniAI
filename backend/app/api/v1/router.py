"""Aggregate v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, agents, auth, chat, documents, escalation, meta, vehicles

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(chat.router)
api_router.include_router(documents.router)
api_router.include_router(escalation.router)
api_router.include_router(vehicles.router)
api_router.include_router(admin.router)
