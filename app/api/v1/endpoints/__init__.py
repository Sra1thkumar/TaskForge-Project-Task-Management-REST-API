from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.workspaces import router as workspaces_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.reports import router as reports_router

__all__ = [
    "auth_router",
    "workspaces_router",
    "projects_router",
    "tasks_router",
    "reports_router",
]
