from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Response
from app.models.user import User
from app.schemas.report import ProductivitySummaryResponse, AuditLogResponse
from app.services.report_service import ReportService
from app.api.deps import get_report_service, get_current_user

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get(
    "/summary",
    response_model=ProductivitySummaryResponse,
    summary="Get Task & Productivity Statistics",
    description="Calculate completed, pending, and overdue tasks, along with completion rate and breakdowns.",
)
def get_productivity_summary(
    workspace_id: Optional[int] = Query(None, description="Scope summary to a specific workspace"),
    project_id: Optional[int] = Query(None, description="Scope summary to a specific project"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user),
):
    return report_service.generate_summary(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
    )


@router.get(
    "/export/csv",
    summary="Export Tasks to CSV",
    description="Generate and download a CSV report containing accessible tasks.",
)
def export_tasks_csv(
    workspace_id: Optional[int] = Query(None, description="Filter exported tasks by workspace"),
    project_id: Optional[int] = Query(None, description="Filter exported tasks by project"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user),
):
    csv_content = report_service.export_tasks_csv(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=workflow_pro_tasks.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="View Audit History",
    description="Review audit logs of creations, updates, deletions, and status transitions.",
)
def get_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (task, project, workspace)"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    actor_id: Optional[int] = Query(None, description="Filter by actor ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    report_service: ReportService = Depends(get_report_service),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * page_size
    logs, _ = report_service.get_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        skip=skip,
        limit=page_size,
    )
    return logs
