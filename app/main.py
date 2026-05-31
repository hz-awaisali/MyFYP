"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.applications.category_router import router as categories_router
from app.applications.router import router as applications_router
from app.attachments.router import router as attachments_router
from app.audit_logs.router import router as audit_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import register_middleware
from app.departments.router import router as departments_router
from app.notifications.router import router as notifications_router
from app.roles.router import router as roles_router
from app.system_settings.router import router as settings_router
from app.users.router import router as users_router
from app.workflows.router import router as workflows_router

logger = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description=(
            "Smart University Management System - backend API. "
            "Phase 1: auth, RBAC, users, university structure, dynamic applications, "
            "workflow engine, notifications, attachments and audit logging."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_middleware(app)
    register_exception_handlers(app)

    api = settings.API_V1_PREFIX
    app.include_router(auth_router, prefix=api)
    app.include_router(roles_router, prefix=api)
    app.include_router(users_router, prefix=api)
    app.include_router(departments_router, prefix=api)
    app.include_router(categories_router, prefix=api)
    app.include_router(applications_router, prefix=api)
    app.include_router(workflows_router, prefix=api)
    app.include_router(notifications_router, prefix=api)
    app.include_router(attachments_router, prefix=api)
    app.include_router(audit_router, prefix=api)
    app.include_router(settings_router, prefix=api)

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": __version__}

    @app.get("/", tags=["Health"])
    async def root():
        return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}

    return app


app = create_app()
