"""Database Seed Script for WorkFlow Pro API.

Populates the database with realistic demo data:
- 4 Users with varied roles (Admin, Project Manager, Senior Developer, QA Engineer)
- 2 Workspaces with member associations
- 3 Projects with varied statuses
- 8 Tasks with diverse priorities, statuses, deadlines, and assignees
- Audit log activity entries
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.audit_log import AuditLog


def seed_database():
    print("[*] Starting database seed process...")
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_admin = db.query(User).filter(User.email == "admin@workflowpro.io").first()
        if existing_admin:
            print("[!] Database already contains seed data (admin@workflowpro.io exists).")
            print_credentials()
            return

        now = datetime.now(timezone.utc)

        # 1. Create Users
        print("[+] Creating demo users...")
        users = [
            User(
                email="admin@workflowpro.io",
                full_name="Alexander Vance (Admin)",
                password_hash=hash_password("AdminPass123!"),
                role=UserRole.ADMIN,
                is_active=True,
            ),
            User(
                email="sarah.manager@workflowpro.io",
                full_name="Sarah Jenkins (Project Manager)",
                password_hash=hash_password("ManagerPass123!"),
                role=UserRole.PROJECT_MANAGER,
                is_active=True,
            ),
            User(
                email="alex.dev@workflowpro.io",
                full_name="Alex Rivera (Lead Engineer)",
                password_hash=hash_password("DevPass123!"),
                role=UserRole.MEMBER,
                is_active=True,
            ),
            User(
                email="maria.qa@workflowpro.io",
                full_name="Maria Chen (QA Specialist)",
                password_hash=hash_password("QAPass123!"),
                role=UserRole.MEMBER,
                is_active=True,
            ),
        ]
        db.add_all(users)
        db.commit()
        for u in users:
            db.refresh(u)

        admin, manager, dev, qa = users

        # 2. Create Workspaces
        print("[+] Creating demo workspaces...")
        ws_fintech = Workspace(
            name="FinTech Solutions Hub",
            description="High-frequency payment processing and security infrastructure",
            owner_id=manager.id,
        )
        ws_mobile = Workspace(
            name="Consumer Mobile Apps",
            description="Cross-platform iOS and Android user-facing applications",
            owner_id=admin.id,
        )
        db.add_all([ws_fintech, ws_mobile])
        db.commit()
        db.refresh(ws_fintech)
        db.refresh(ws_mobile)

        # 3. Add Workspace Memberships
        memberships = [
            # FinTech Workspace: Manager is Admin, Dev is Project Manager, QA is Member
            WorkspaceMember(workspace_id=ws_fintech.id, user_id=manager.id, role=WorkspaceRole.ADMIN),
            WorkspaceMember(workspace_id=ws_fintech.id, user_id=dev.id, role=WorkspaceRole.PROJECT_MANAGER),
            WorkspaceMember(workspace_id=ws_fintech.id, user_id=qa.id, role=WorkspaceRole.MEMBER),
            # Mobile Apps Workspace: Admin is Admin, Dev is Member
            WorkspaceMember(workspace_id=ws_mobile.id, user_id=admin.id, role=WorkspaceRole.ADMIN),
            WorkspaceMember(workspace_id=ws_mobile.id, user_id=dev.id, role=WorkspaceRole.MEMBER),
        ]
        db.add_all(memberships)
        db.commit()

        # 4. Create Projects
        print("[+] Creating demo projects...")
        proj_payments = Project(
            workspace_id=ws_fintech.id,
            name="Stripe & Crypto Gateway V2",
            description="Multi-currency checkout flow and automated webhook settlement",
            status=ProjectStatus.IN_PROGRESS,
            created_by_id=manager.id,
        )
        proj_security = Project(
            workspace_id=ws_fintech.id,
            name="SOC-2 Compliance & Audit Trail",
            description="Data retention policies and immutable cryptographic audit logging",
            status=ProjectStatus.COMPLETED,
            created_by_id=manager.id,
        )
        proj_mobile = Project(
            workspace_id=ws_mobile.id,
            name="Biometric Auth & FaceID",
            description="Native device authentication integration for mobile clients",
            status=ProjectStatus.PLANNING,
            created_by_id=admin.id,
        )
        db.add_all([proj_payments, proj_security, proj_mobile])
        db.commit()
        db.refresh(proj_payments)
        db.refresh(proj_security)
        db.refresh(proj_mobile)

        # 5. Create Tasks
        print("[+] Creating demo tasks with deadlines & priorities...")
        tasks = [
            # Payment Gateway Tasks
            Task(
                project_id=proj_payments.id,
                title="Implement Webhook Signature Verification",
                description="Verify HMAC signatures on incoming Stripe charge events.",
                priority=TaskPriority.URGENT,
                status=TaskStatus.IN_PROGRESS,
                due_date=now + timedelta(days=2),
                assignee_id=dev.id,
                created_by_id=manager.id,
            ),
            Task(
                project_id=proj_payments.id,
                title="Rate Limiter Middleware for Checkout Endpoint",
                description="Prevent card testing attacks using Redis token bucket algorithm.",
                priority=TaskPriority.HIGH,
                status=TaskStatus.TODO,
                due_date=now + timedelta(days=5),
                assignee_id=dev.id,
                created_by_id=manager.id,
            ),
            Task(
                project_id=proj_payments.id,
                title="End-to-End Sandbox Transaction Testing",
                description="Run simulated payment failures, 3D Secure verification, and refund flows.",
                priority=TaskPriority.HIGH,
                status=TaskStatus.IN_REVIEW,
                due_date=now + timedelta(days=3),
                assignee_id=qa.id,
                created_by_id=manager.id,
            ),
            Task(
                project_id=proj_payments.id,
                title="Database Migration for Order Schema",
                description="Add currency, idempotency_key, and ledger_reference columns.",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.COMPLETED,
                due_date=now - timedelta(days=1),
                assignee_id=dev.id,
                created_by_id=manager.id,
            ),
            # Overdue Task (demonstrates overdue reporting in /reports/summary!)
            Task(
                project_id=proj_payments.id,
                title="Update PCI-DSS Documentation",
                description="Review network boundary diagrams with external auditors.",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.TODO,
                due_date=now - timedelta(days=3),
                assignee_id=manager.id,
                created_by_id=admin.id,
            ),
            # Security Project Tasks (all completed)
            Task(
                project_id=proj_security.id,
                title="Argon2 Password Hashing Benchmark",
                description="Benchmark memory and CPU parameters for 64MB memory cost.",
                priority=TaskPriority.HIGH,
                status=TaskStatus.COMPLETED,
                due_date=now - timedelta(days=4),
                assignee_id=dev.id,
                created_by_id=manager.id,
            ),
            Task(
                project_id=proj_security.id,
                title="Alembic DDL Execution Plan Review",
                description="Verify zero-downtime column migrations on production database.",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.COMPLETED,
                due_date=now - timedelta(days=2),
                assignee_id=dev.id,
                created_by_id=manager.id,
            ),
            # Mobile Project Task
            Task(
                project_id=proj_mobile.id,
                title="Evaluate WebAuthn vs FaceID Protocol",
                description="Draft RFC comparing biometric key security enclaves.",
                priority=TaskPriority.LOW,
                status=TaskStatus.TODO,
                due_date=now + timedelta(days=10),
                assignee_id=dev.id,
                created_by_id=admin.id,
            ),
        ]
        db.add_all(tasks)
        db.commit()

        # 6. Audit Logs
        print("[+] Logging initial change events...")
        logs = [
            AuditLog(
                actor_id=manager.id,
                action="CREATE",
                entity_type="workspace",
                entity_id=ws_fintech.id,
                changes='{"name": "FinTech Solutions Hub"}',
                created_at=now - timedelta(days=10),
            ),
            AuditLog(
                actor_id=manager.id,
                action="CREATE",
                entity_type="project",
                entity_id=proj_payments.id,
                changes='{"name": "Stripe & Crypto Gateway V2"}',
                created_at=now - timedelta(days=8),
            ),
            AuditLog(
                actor_id=dev.id,
                action="STATUS_CHANGE",
                entity_type="task",
                entity_id=tasks[3].id,
                changes='{"status": {"old": "in_progress", "new": "completed"}}',
                created_at=now - timedelta(days=1),
            ),
        ]
        db.add_all(logs)
        db.commit()

        print("[OK] Database seeding completed successfully!\n")
        print_credentials()

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during database seeding: {e}")
        raise
    finally:
        db.close()


def print_credentials():
    print("=" * 72)
    print("  DEMO USERS READY FOR TESTING (Swagger UI: http://127.0.0.1:8000/docs)")
    print("=" * 72)
    print(f"{'Role':<18} | {'Email':<32} | {'Password'}")
    print("-" * 72)
    print(f"{'System Admin':<18} | {'admin@workflowpro.io':<32} | {'AdminPass123!'}")
    print(f"{'Project Manager':<18} | {'sarah.manager@workflowpro.io':<32} | {'ManagerPass123!'}")
    print(f"{'Senior Developer':<18} | {'alex.dev@workflowpro.io':<32} | {'DevPass123!'}")
    print(f"{'QA Specialist':<18} | {'maria.qa@workflowpro.io':<32} | {'QAPass123!'}")
    print("=" * 72)
    print("[*] TIP: Click 'Authorize' in Swagger UI and login with any of these!")
    print("=" * 72)



if __name__ == "__main__":
    seed_database()
