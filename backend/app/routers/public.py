"""The new-employee submission form — an open, self-service joining flow.

Admin/HR simply share the joining link; the applicant starts their own
submission here.

  * ``POST /api/public/submissions`` creates a fresh submission and returns
    its reference code — the only handle the applicant needs to come back,
    add documents, and track the outcome;
  * the only openly readable reference data is the *names* of
    organisations, designations and campuses needed to fill the dropdowns;
  * nothing here ever enters the directory — HR/Admin/Department Head must
    review and approve it first.
"""
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    Designation,
    EmployeeSubmission,
    Location,
    OrgUnit,
    OrgUnitKind,
    SubmissionDocument,
    SubmissionStatus,
)
from app.schemas.schemas import (
    OrgUnitNode,
    PublicOption,
    SubmissionCreated,
    SubmissionDocumentOut,
    SubmissionPublicOut,
    SubmissionUpdate,
)
from app.services import storage
from app.services.org import employee_counts_by_unit, sanctioned_counts_by_unit

router = APIRouter(prefix="/api/public", tags=["Public submission"])

SCOPE = "submissions"
MAX_DOCUMENTS_PER_SUBMISSION = 15

# States in which the applicant may still change their own submission.
EDITABLE_STATES = {
    SubmissionStatus.draft,
    SubmissionStatus.resubmission_required,
}

REQUIRED_FOR_SUBMIT = (
    ("Full name", "full_name"),
    ("Phone number", "phone"),
    ("Date of birth", "date_of_birth"),
    ("Father's name", "father_name"),
    ("Aadhaar number", "aadhaar_number"),
    ("Permanent address", "permanent_address"),
)


def next_reference_code(db: Session) -> str:
    count = db.query(func.count(EmployeeSubmission.id)).scalar() or 0
    return f"AVFU-SUB-{count + 1:06d}"


def _load(db: Session, reference_code: str) -> EmployeeSubmission:
    """Fetch a submission by its reference code."""
    record = (
        db.query(EmployeeSubmission)
        .filter(EmployeeSubmission.reference_code == reference_code.strip().upper())
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No submission matches that reference code",
        )
    return record


def _public_out(record: EmployeeSubmission) -> SubmissionPublicOut:
    return SubmissionPublicOut(
        reference_code=record.reference_code,
        status=record.status,
        full_name=record.full_name,
        email=record.email,
        phone=record.phone,
        gender=record.gender,
        date_of_birth=record.date_of_birth,
        date_of_joining_aau_avfu=record.date_of_joining_aau_avfu,
        date_of_joining_present_post=record.date_of_joining_present_post,
        expected_date_of_retirement=record.expected_date_of_retirement,
        org_unit_id=record.org_unit_id,
        org_unit=record.org_unit.name if record.org_unit else None,
        designation_id=record.designation_id,
        designation=record.designation.name if record.designation else None,
        location_id=record.location_id,
        location=record.location.name if record.location else None,
        date_of_joining=record.date_of_joining,
        father_name=record.father_name,
        mother_name=record.mother_name,
        blood_group=record.blood_group,
        marital_status=record.marital_status,
        nationality=record.nationality,
        category=record.category,
        aadhaar_number=record.aadhaar_number,
        pan_number=record.pan_number,
        emergency_contact_name=record.emergency_contact_name,
        emergency_contact_phone=record.emergency_contact_phone,
        permanent_address=record.permanent_address,
        present_address=record.present_address,
        bank_name=record.bank_name,
        bank_account_number=record.bank_account_number,
        bank_ifsc=record.bank_ifsc,
        submitted_at=record.submitted_at,
        reviewed_at=record.reviewed_at,
        reviewer_remark=record.reviewer_remark,
        documents=[SubmissionDocumentOut.model_validate(d) for d in record.documents],
        can_edit=record.status in EDITABLE_STATES,
        hrms_employee_id=(
            record.created_employee.hrms_employee_id
            if record.created_employee
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Reference data for the form's dropdowns — names only, nothing restricted
# ---------------------------------------------------------------------------
@router.get("/org-units", response_model=list[PublicOption])
def public_org_units(db: Session = Depends(get_db)):
    """Offices an applicant can be joining. Names only — no staff or counts."""
    rows = (
        db.query(OrgUnit)
        .filter(
            OrgUnit.is_active.is_(True),
            OrgUnit.kind.in_(
                [OrgUnitKind.establishment, OrgUnitKind.department, OrgUnitKind.section]
            ),
        )
        .order_by(OrgUnit.sort_order, OrgUnit.name)
        .all()
    )
    return [
        PublicOption(id=o.id, name=o.name, group=o.kind.value) for o in rows
    ]


@router.get("/designations", response_model=list[PublicOption])
def public_designations(db: Session = Depends(get_db)):
    rows = (
        db.query(Designation)
        .filter(Designation.is_active.is_(True))
        .order_by(Designation.rank_level, Designation.name)
        .all()
    )
    return [
        PublicOption(id=d.id, name=d.name, group=d.category.value) for d in rows
    ]


@router.get("/locations", response_model=list[PublicOption])
def public_locations(db: Session = Depends(get_db)):
    rows = (
        db.query(Location)
        .filter(Location.is_active.is_(True))
        .order_by(Location.name)
        .all()
    )
    return [PublicOption(id=l.id, name=l.name) for l in rows]


@router.get("/document-types", response_model=list[str])
def public_document_types(org_unit_id: int | None = None, db: Session = Depends(get_db)):
    """Built-in document types plus any HR-defined ones for this department."""
    from app.routers.custom_fields import applicable_document_labels

    return storage.DOCUMENT_TYPES + applicable_document_labels(db, org_unit_id)


@router.get("/org-unit-tree", response_model=list[OrgUnitNode])
def public_org_unit_tree(db: Session = Depends(get_db)):
    """The AVFU hierarchy, viewable without signing in.

    The structure carries no restricted data, so the same shape a
    signed-in user sees at ``/api/org-units/tree`` is safe to hand to a
    visitor. Names of heads/officers-in-charge are included; the frontend
    renders them as plain text for anonymous visitors (the directory they
    would link to still needs a login).
    """
    units = (
        db.query(OrgUnit)
        .filter(OrgUnit.is_active.is_(True))
        .order_by(OrgUnit.sort_order, OrgUnit.name)
        .all()
    )
    emp_direct = employee_counts_by_unit(db)
    sanc_direct = sanctioned_counts_by_unit(db)

    by_parent: dict[int | None, list[OrgUnit]] = {}
    for u in units:
        by_parent.setdefault(u.parent_id, []).append(u)

    def build(u: OrgUnit) -> OrgUnitNode:
        children = [build(c) for c in by_parent.get(u.id, [])]
        return OrgUnitNode(
            id=u.id,
            name=u.name,
            short_code=u.short_code,
            kind=u.kind,
            sub_kind=u.sub_kind,
            location_name=u.location.name if u.location else None,
            head_name=u.head.full_name if u.head else None,
            head_id=u.head_employee_id,
            officer_in_charge_name=(
                u.officer_in_charge.full_name if u.officer_in_charge else None
            ),
            direct_employee_count=emp_direct.get(u.id, 0),
            total_employee_count=emp_direct.get(u.id, 0)
            + sum(c.total_employee_count for c in children),
            sanctioned_count=sanc_direct.get(u.id, 0)
            + sum(c.sanctioned_count for c in children),
            is_active=u.is_active,
            children=children,
        )

    return [build(r) for r in by_parent.get(None, [])]


# ---------------------------------------------------------------------------
# Submission lifecycle — the applicant tracks their submission by its
# reference code alone
# ---------------------------------------------------------------------------
@router.post(
    "/submissions",
    response_model=SubmissionCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(request: Request, db: Session = Depends(get_db)):
    """Start a new, empty submission and return its reference code."""
    record = EmployeeSubmission(
        reference_code=next_reference_code(db),
        status=SubmissionStatus.draft,
        submitter_ip=request.client.host if request.client else "",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return SubmissionCreated(
        reference_code=record.reference_code, status=record.status
    )


@router.get("/submissions/{reference_code}", response_model=SubmissionPublicOut)
def read_submission(
    reference_code: str,
    db: Session = Depends(get_db),
):
    return _public_out(_load(db, reference_code))


@router.put("/submissions/{reference_code}", response_model=SubmissionPublicOut)
def update_submission(
    reference_code: str,
    payload: SubmissionUpdate,
    db: Session = Depends(get_db),
):
    record = _load(db, reference_code)
    if record.status not in EDITABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"This submission can no longer be edited (it is '{record.status.value}')",
        )
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    if record.status == SubmissionStatus.draft:
        record.status = SubmissionStatus.draft  # stays draft until finalised
    db.commit()
    db.refresh(record)
    return _public_out(record)


@router.post(
    "/submissions/{reference_code}/documents",
    response_model=SubmissionDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_submission_document(
    reference_code: str,
    request: Request,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    record = _load(db, reference_code)
    if record.status not in EDITABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Documents can no longer be changed (submission is '{record.status.value}')",
        )
    if len(record.documents) >= MAX_DOCUMENTS_PER_SUBMISSION:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_DOCUMENTS_PER_SUBMISSION} documents can be attached",
        )

    stored_name, contents = storage.save_upload(SCOPE, record.id, file)
    doc = SubmissionDocument(
        submission_id=record.id,
        doc_type=doc_type,
        original_filename=file.filename or stored_name,
        stored_filename=stored_name,
        content_type=file.content_type or "",
        size_bytes=len(contents),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return SubmissionDocumentOut.model_validate(doc)


@router.delete(
    "/submissions/{reference_code}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_submission_document(
    reference_code: str,
    doc_id: int,
    db: Session = Depends(get_db),
):
    record = _load(db, reference_code)
    if record.status not in EDITABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Documents can no longer be changed (submission is '{record.status.value}')",
        )
    doc = db.get(SubmissionDocument, doc_id)
    if doc is None or doc.submission_id != record.id:
        raise HTTPException(status_code=404, detail="Document not found")
    storage.delete_file(SCOPE, record.id, doc.stored_filename)
    db.delete(doc)
    db.commit()


@router.get("/submissions/{reference_code}/documents/{doc_id}/file")
def download_submission_document(
    reference_code: str,
    doc_id: int,
    db: Session = Depends(get_db),
):
    record = _load(db, reference_code)
    doc = db.get(SubmissionDocument, doc_id)
    if doc is None or doc.submission_id != record.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return storage.send_file(
        SCOPE, record.id, doc.stored_filename, doc.content_type, doc.original_filename
    )


@router.post("/submissions/{reference_code}/submit", response_model=SubmissionPublicOut)
def finalise_submission(
    reference_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.core import audit
    from app.core.deps import client_ip

    record = _load(db, reference_code)
    if record.status not in EDITABLE_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"This submission has already been sent (it is '{record.status.value}')",
        )

    missing = [label for label, field in REQUIRED_FOR_SUBMIT if not getattr(record, field)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Complete these fields before submitting: " + ", ".join(missing),
        )
    if not record.documents:
        raise HTTPException(
            status_code=400, detail="Attach at least one supporting document"
        )

    record.status = SubmissionStatus.submitted
    record.submitted_at = datetime.now(timezone.utc)
    record.reviewer_remark = ""
    audit.log(
        db,
        None,
        "submission.submitted",
        entity_type="submission",
        entity_id=record.id,
        summary=(
            f"{record.full_name} submitted {record.reference_code} with "
            f"{len(record.documents)} document(s)"
        ),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _public_out(record)
