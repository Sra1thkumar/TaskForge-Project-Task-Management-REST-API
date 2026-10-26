from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class StatusBreakdown(BaseModel):
    todo: int = 0
    in_progress: int = 0
    in_review: int = 0
    completed: int = 0
    blocked: int = 0


class PriorityBreakdown(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    urgent: int = 0


class AssigneeProductivity(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    total_assigned: int
    completed: int
    pending: int
    overdue: int
    completion_rate: float


class ProjectProductivity(BaseModel):
    project_id: int
    project_name: str
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    completion_percentage: float


class ProductivitySummaryResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    completion_rate: float
    status_breakdown: StatusBreakdown
    priority_breakdown: PriorityBreakdown
    assignee_breakdown: List[AssigneeProductivity]
    project_breakdown: List[ProjectProductivity]


class AuditLogResponse(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor: Optional[UserResponse] = None
    action: str
    entity_type: str
    entity_id: int
    changes: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
