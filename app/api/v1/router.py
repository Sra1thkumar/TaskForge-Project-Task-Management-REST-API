from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth_router,
    workspaces_router,
    projects_router,
    tasks_router,
    reports_router,
)

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(reports_router)
