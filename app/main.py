import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.exceptions import AppException
from app.api.v1.router import api_router
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist (especially in local dev / sqlite mode)
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Performance & audit header middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


# Application exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


from fastapi.responses import JSONResponse, HTMLResponse


LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WorkFlow Pro API</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --card-bg: rgba(22, 27, 46, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.25);
            --accent-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            --success: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
            position: relative;
            overflow-x: hidden;
        }
        .ambient-glow {
            position: absolute;
            width: 600px;
            height: 600px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.18) 0%, rgba(168, 85, 247, 0.06) 50%, transparent 70%);
            top: -150px;
            left: 50%;
            transform: translateX(-50%);
            pointer-events: none;
            z-index: 0;
        }
        .container {
            max-width: 860px;
            width: 100%;
            position: relative;
            z-index: 1;
        }
        .header {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
        }
        .badge-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }
        h1 {
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.75rem;
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            font-size: 1.15rem;
            color: var(--text-muted);
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.5rem;
            text-decoration: none;
            color: inherit;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
            backdrop-filter: blur(12px);
            position: relative;
        }
        .card:hover {
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 12px 30px -10px var(--accent-glow);
        }
        .card-icon {
            font-size: 1.75rem;
            margin-bottom: 1rem;
        }
        .card-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
            color: var(--text-main);
        }
        .card-desc {
            font-size: 0.9rem;
            color: var(--text-muted);
            line-height: 1.5;
            flex-grow: 1;
        }
        .card-action {
            margin-top: 1.25rem;
            font-size: 0.85rem;
            font-weight: 600;
            color: #818cf8;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }
        .card:hover .card-action {
            color: #a5b4fc;
        }
        .features-pill-row {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.75rem;
            padding-top: 1rem;
            border-top: 1px solid var(--card-border);
        }
        .pill {
            font-size: 0.8rem;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--card-border);
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            color: var(--text-muted);
        }
        footer {
            margin-top: 2.5rem;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        footer a {
            color: #818cf8;
            text-decoration: none;
        }
        footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="ambient-glow"></div>
    <div class="container">
        <header class="header">
            <div class="badge">
                <span class="badge-dot"></span>
                <span>System Operational • v1.0.0</span>
            </div>
            <h1>WorkFlow Pro</h1>
            <p class="subtitle">A secure, multi-tenant Project & Task Management REST API built with FastAPI, PostgreSQL, SQLAlchemy 2.0, JWT & Celery.</p>
        </header>

        <div class="grid">
            <a href="/docs" class="card">
                <div class="card-icon">⚡</div>
                <div class="card-title">Interactive Swagger Docs</div>
                <div class="card-desc">Test all REST endpoints in real-time, execute queries, and authorize with JWT tokens.</div>
                <div class="card-action">Open Swagger UI &rarr;</div>
            </a>

            <a href="/redoc" class="card">
                <div class="card-icon">📘</div>
                <div class="card-title">ReDoc Documentation</div>
                <div class="card-desc">Clean, structured OpenAPI specification with complete request & response schemas.</div>
                <div class="card-action">View ReDoc &rarr;</div>
            </a>

            <a href="/health" class="card">
                <div class="card-icon">🩺</div>
                <div class="card-title">Health Check</div>
                <div class="card-desc">Monitor live API heartbeat, deployment environment, and engine status.</div>
                <div class="card-action">Inspect Status &rarr;</div>
            </a>

            <a href="/api/v1/reports/summary" class="card">
                <div class="card-icon">📊</div>
                <div class="card-title">Analytics & Reports</div>
                <div class="card-desc">Productivity summaries, task metrics, and downloadable CSV exports.</div>
                <div class="card-action">Explore Reports &rarr;</div>
            </a>
        </div>

        <div class="features-pill-row">
            <span class="pill">🔒 Argon2id + JWT Auth</span>
            <span class="pill">🏢 Multi-Tenant Workspaces</span>
            <span class="pill">📋 Advanced Task Workflows</span>
            <span class="pill">⏱️ Celery & Redis Queues</span>
            <span class="pill">🗄️ PostgreSQL & Alembic</span>
            <span class="pill">🧪 100% Pytest Covered</span>
        </div>

        <footer>
            <span>WorkFlow Pro API &bull; Built with FastAPI &bull; </span>
            <a href="https://github.com/Sra1thkumar/TaskForge-Project-Task-Management-REST-API" target="_blank" rel="noopener">GitHub Repository</a>
        </footer>
    </div>
</body>
</html>
"""


# Root endpoint
@app.get(
    "/",
    tags=["System"],
    summary="API Root Navigation",
    description="Welcome landing page with quick navigation links to Swagger UI, ReDoc, and Health Check.",
)
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(content=LANDING_HTML)
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "status": "online",
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api_v1": settings.API_V1_STR,
    }


# Health check endpoint
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Check the operational status of the WorkFlow Pro API.",
)
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include v1 API routes
app.include_router(api_router, prefix=settings.API_V1_STR)
