import os
os.environ["TESTING"] = "true"
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.project import Project, ProjectStatus

# In-memory SQLite for blazing-fast, isolated automated testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        email="admin@workflowpro.io",
        full_name="System Admin",
        password_hash=hash_password("adminSecret123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=admin_user.id, role=admin_user.role.value)


@pytest.fixture
def manager_user(db_session: Session) -> User:
    user = User(
        email="manager@workflowpro.io",
        full_name="Project Manager Alice",
        password_hash=hash_password("managerSecret123!"),
        role=UserRole.PROJECT_MANAGER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_token(manager_user: User) -> str:
    return create_access_token(subject=manager_user.id, role=manager_user.role.value)


@pytest.fixture
def member_user(db_session: Session) -> User:
    user = User(
        email="developer@workflowpro.io",
        full_name="Developer Bob",
        password_hash=hash_password("memberSecret123!"),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def member_token(member_user: User) -> str:
    return create_access_token(subject=member_user.id, role=member_user.role.value)


@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        email="outsider@external.com",
        full_name="Outsider Charlie",
        password_hash=hash_password("outsiderSecret123!"),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_token(other_user: User) -> str:
    return create_access_token(subject=other_user.id, role=other_user.role.value)


@pytest.fixture
def sample_workspace(db_session: Session, manager_user: User, member_user: User) -> Workspace:
    ws = Workspace(
        name="Alpha Engineering",
        description="Engineering workspace for taskforge/workflow-pro",
        owner_id=manager_user.id,
    )
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)

    # Add manager as Admin
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=manager_user.id, role=WorkspaceRole.ADMIN)
    # Add member as Member
    m2 = WorkspaceMember(workspace_id=ws.id, user_id=member_user.id, role=WorkspaceRole.MEMBER)
    db_session.add_all([m1, m2])
    db_session.commit()
    return ws


@pytest.fixture
def sample_project(db_session: Session, sample_workspace: Workspace, manager_user: User) -> Project:
    proj = Project(
        workspace_id=sample_workspace.id,
        name="Backend Core V1",
        description="Develop REST API backend with FastAPI",
        status=ProjectStatus.IN_PROGRESS,
        created_by_id=manager_user.id,
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)
    return proj
