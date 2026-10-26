import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: int,
        actor_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        changes_json = json.dumps(changes, default=str) if changes else None
        audit_entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes_json,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        return audit_entry

    def list(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditLog], int]:
        query = select(AuditLog)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        items = list(
            self.db.execute(
                query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
            ).scalars().all()
        )
        return items, total
