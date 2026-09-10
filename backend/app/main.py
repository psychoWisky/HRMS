from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.models import models  # noqa: F401  (register models)
from app.routers import (
    admin_users,
    auth,
    custom_fields,
    dashboard,
    designations,
    directory,
    employees,
    kyc,
    org_units,
    public,
    submissions,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AVFU HRMS API",
    description=(
        "One centralised Human Resource Management System for "
        "Assam Veterinary and Fishery University.\n\n"
        "Four roles: Administrator and HR (full access), Department Head "
        "(HR-like access scoped to one department) and the hidden Super "
        "Admin technical role. Every endpoint outside `/api/public` "
        "requires a bearer token and is guarded by an explicit permission.\n\n"
        "`/api/public` is the open, self-service new-employee submission "
        "form. Admin/HR share the joining link; the applicant starts their "
        "own submission and tracks it by its reference code."
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    public.router,  # open, no login — see its own docstring
    auth.router,
    employees.router,
    directory.router,
    org_units.router,
    designations.router,
    custom_fields.router,
    custom_fields.doc_router,
    submissions.router,
    kyc.router,
    dashboard.router,
    admin_users.router,
):
    app.include_router(r)


@app.get("/", tags=["Meta"])
def root():
    return {
        "app": "AVFU HRMS API",
        "university": settings.UNIVERSITY_NAME,
        "version": app.version,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Meta"])
def health():
    return {"status": "healthy"}
