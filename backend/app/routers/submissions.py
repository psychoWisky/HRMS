"""HR/Department-Head review of new-employee submissions.

Applicants create their own submission from the public joining link that
Admin/HR share; there is no token to issue. Approving a submission is the
only path by which it becomes a real ``Employee`` record.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, require_perm
from app.core.permissions import SUBMISSION_REVIEW
from app.models.models import (
    KYC,
    Designation,
    Employee,
    EmployeeSubmission,
    KYCDocument,
    KYCHistory,
    KYCStatus,
    Location,
    OrgUnit,
    Post,
    ReportingRelationship,
    SubmissionDocument,
    SubmissionStatus,
    User,
)
from app.schemas.schemas import (
    SubmissionAdminOut,
    SubmissionApproval,
    SubmissionDecision,
    SubmissionDocumentOut,
)
from app.services import storage
from app.services.hierarchy import would_create_reporting_cycle
from app.services.org import department_scope_ids
from app.services.retirement import calc_retirement_date

router = APIRouter(tags=["Submission review"])
submissions_router = APIRouter(prefix="/api/submissions", tags=["Submission review"])

SCOPE = "submissions"
KYC_SCOPE = "kyc"

REVIEWABLE = {SubmissionStatus.submitted, SubmissionStatus.under_review}


def _admin_out(db: Session, record: EmployeeSubmission) -> SubmissionAdminOut:
    return SubmissionAdminOut(
        id=record.id,
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
        can_edit=False,
        hrms_employee_id=(
            record.created_employee.hrms_employee_id
            if record.created_employee
            else None
        ),
        created_at=record.created_at,
        submitter_ip=record.submitter_ip,
        reviewed_by_name=record.reviewed_by.email if record.reviewed_by else None,
        created_employee_id=record.created_employee_id,
    )


def _apply_department_scope(db: Session, user: User, query):
    scope = department_scope_ids(db, user)
    if scope is None:
        return query
    return query.filter(
        or_(
            EmployeeSubmission.org_unit_id.in_(scope),
            EmployeeSubmission.org_unit_id.is_(None),
        )
    )


def _assert_submission_in_scope(db: Session, user: User, record: EmployeeSubmission) -> None:
    scope = department_scope_ids(db, user)
    if scope is None:
        return
    if record.org_unit_id is not None and record.org_unit_id not in scope:
        raise HTTPException(
            status_code=403,
            detail="This submission is outside the department you manage",
        )


# ---------------------------------------------------------------------------
# Submission review (Admin/HR/Department Head)
# ---------------------------------------------------------------------------
@submissions_router.get("", response_model=list[SubmissionAdminOut])
def list_submissions(
    submission_status: SubmissionStatus | None = None,
    q: str = "",
    limit: int = Query(300, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    query = db.query(EmployeeSubmission)
    if submission_status is not None:
        query = query.filter(EmployeeSubmission.status == submission_status)
    else:
        # Untouched token shells are noise; hide them unless asked for.
        query = query.filter(EmployeeSubmission.status != SubmissionStatus.draft)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                EmployeeSubmission.full_name.ilike(like),
                EmployeeSubmission.reference_code.ilike(like),
                EmployeeSubmission.email.ilike(like),
            )
        )
    query = _apply_department_scope(db, user, query)
    rows = (
        query.order_by(EmployeeSubmission.submitted_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_admin_out(db, r) for r in rows]


@submissions_router.get("/{submission_id}", response_model=SubmissionAdminOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    return _admin_out(db, record)


@submissions_router.get("/{submission_id}/documents/{doc_id}/file")
def download_document(
    submission_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    doc = db.get(SubmissionDocument, doc_id)
    if doc is None or doc.submission_id != submission_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return storage.send_file(
        SCOPE, submission_id, doc.stored_filename, doc.content_type, doc.original_filename
    )


@submissions_router.post("/{submission_id}/start-review", response_model=SubmissionAdminOut)
def start_review(
    submission_id: int,
    payload: SubmissionDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    if record.status != SubmissionStatus.submitted:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start review of a '{record.status.value}' submission",
        )
    record.status = SubmissionStatus.under_review
    record.reviewed_by_id = user.id
    record.reviewed_at = datetime.now(timezone.utc)
    record.reviewer_remark = payload.remark
    audit.log(
        db,
        user,
        "submission.under_review",
        entity_type="submission",
        entity_id=record.id,
        summary=f"Started review of {record.reference_code} ({record.full_name})",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _admin_out(db, record)


@submissions_router.post(
    "/{submission_id}/request-resubmission", response_model=SubmissionAdminOut
)
def request_resubmission(
    submission_id: int,
    payload: SubmissionDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    if not payload.remark.strip():
        raise HTTPException(
            status_code=400,
            detail="Explain what the applicant must correct before resubmitting",
        )
    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    if record.status not in REVIEWABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot act on a '{record.status.value}' submission",
        )
    record.status = SubmissionStatus.resubmission_required
    record.reviewed_by_id = user.id
    record.reviewed_at = datetime.now(timezone.utc)
    record.reviewer_remark = payload.remark
    audit.log(
        db,
        user,
        "submission.resubmission_required",
        entity_type="submission",
        entity_id=record.id,
        summary=f"Requested resubmission for {record.reference_code}",
        detail={"remark": payload.remark},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _admin_out(db, record)


@submissions_router.post("/{submission_id}/reject", response_model=SubmissionAdminOut)
def reject_submission(
    submission_id: int,
    payload: SubmissionDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    if not payload.remark.strip():
        raise HTTPException(
            status_code=400, detail="A reason is required when rejecting a submission"
        )
    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    if record.status not in REVIEWABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot act on a '{record.status.value}' submission",
        )
    record.status = SubmissionStatus.rejected
    record.reviewed_by_id = user.id
    record.reviewed_at = datetime.now(timezone.utc)
    record.reviewer_remark = payload.remark
    audit.log(
        db,
        user,
        "submission.rejected",
        entity_type="submission",
        entity_id=record.id,
        summary=f"Rejected {record.reference_code} ({record.full_name})",
        detail={"remark": payload.remark},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _admin_out(db, record)


@submissions_router.post("/{submission_id}/approve", response_model=SubmissionAdminOut)
def approve_submission(
    submission_id: int,
    payload: SubmissionApproval,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    """Admit the applicant into the HRMS.

    Creates the employee record with a permanent HRMS Employee ID (in the
    AVFU/<Establishment Short Form>/<seq> format when the target
    establishment has one configured) and moves the submitted documents
    onto a verified KYC record. No login account is created.
    """
    from app.routers.employees import _generate_id

    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    if record.status not in REVIEWABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve a '{record.status.value}' submission",
        )
    if record.created_employee_id:
        raise HTTPException(
            status_code=400, detail="This submission has already been admitted"
        )

    org_unit_id = payload.org_unit_id or record.org_unit_id
    designation_id = payload.designation_id or record.designation_id
    location_id = payload.location_id or record.location_id

    for value, model, label in (
        (org_unit_id, OrgUnit, "Office / org unit"),
        (designation_id, Designation, "Designation"),
        (location_id, Location, "Campus"),
        (payload.post_id, Post, "Post"),
    ):
        if value is not None and db.get(model, value) is None:
            raise HTTPException(status_code=400, detail=f"{label} not found")

    hrms_id = (payload.hrms_employee_id or "").strip() or _generate_id(
        db, org_unit_id
    )
    if db.query(Employee).filter(Employee.hrms_employee_id == hrms_id).first():
        raise HTTPException(
            status_code=409, detail=f"HRMS Employee ID {hrms_id} is already in use"
        )

    dob = record.date_of_birth
    designation = db.get(Designation, designation_id) if designation_id else None
    expected_retirement = (
        payload.expected_date_of_retirement
        or record.expected_date_of_retirement
        or calc_retirement_date(dob, designation.rank_level if designation else None)
    )

    employee = Employee(
        hrms_employee_id=hrms_id,
        full_name=record.full_name,
        gender=record.gender,
        date_of_birth=dob,
        date_of_joining_aau_avfu=(
            payload.date_of_joining_aau_avfu or record.date_of_joining_aau_avfu
        ),
        date_of_joining_present_post=(
            payload.date_of_joining_present_post or record.date_of_joining_present_post
        ),
        expected_date_of_retirement=expected_retirement,
        official_email=record.email,
        phone=record.phone,
        org_unit_id=org_unit_id,
        location_id=location_id,
        designation_id=designation_id,
        post_id=payload.post_id,
        date_of_joining=payload.date_of_joining or record.date_of_joining,
    )
    db.add(employee)
    db.flush()

    from app.models.models import PositionEventType, PositionHistory

    db.add(
        PositionHistory(
            employee_id=employee.id,
            event_type=PositionEventType.joining,
            new_designation_id=designation_id,
            new_org_unit_id=org_unit_id,
            new_employee_code=hrms_id,
            effective_date=employee.date_of_joining or datetime.now(timezone.utc).date(),
            new_position_joining_date=employee.date_of_joining,
            remarks=f"Admitted from submission {record.reference_code}",
            created_by_id=user.id,
        )
    )

    if payload.reports_to_id:
        manager = db.get(Employee, payload.reports_to_id)
        if manager is None:
            raise HTTPException(status_code=400, detail="Reporting authority not found")
        if would_create_reporting_cycle(db, employee.id, manager.id):
            raise HTTPException(
                status_code=400,
                detail="That reporting authority would create a circular hierarchy",
            )
        db.add(
            ReportingRelationship(
                employee_id=employee.id, reports_to_id=manager.id, is_primary=True
            )
        )

    now = datetime.now(timezone.utc)
    kyc = KYC(
        employee_id=employee.id,
        status=KYCStatus.verified,
        father_name=record.father_name,
        mother_name=record.mother_name,
        date_of_birth=record.date_of_birth,
        date_of_joining_aau_avfu=employee.date_of_joining_aau_avfu,
        date_of_joining_present_post=employee.date_of_joining_present_post,
        expected_date_of_retirement=employee.expected_date_of_retirement,
        gender=record.gender,
        blood_group=record.blood_group,
        marital_status=record.marital_status,
        nationality=record.nationality,
        category=record.category,
        aadhaar_number=record.aadhaar_number,
        pan_number=record.pan_number,
        personal_email=record.email,
        contact_phone=record.phone,
        emergency_contact_name=record.emergency_contact_name,
        emergency_contact_phone=record.emergency_contact_phone,
        permanent_address=record.permanent_address,
        present_address=record.present_address,
        bank_name=record.bank_name,
        bank_account_number=record.bank_account_number,
        bank_ifsc=record.bank_ifsc,
        submitted_at=record.submitted_at,
        verified_by_id=user.id,
        verified_at=now,
        verifier_remark=payload.remark,
    )
    db.add(kyc)
    db.flush()

    for doc in record.documents:
        storage.move_file(SCOPE, record.id, KYC_SCOPE, kyc.id, doc.stored_filename)
        db.add(
            KYCDocument(
                kyc_id=kyc.id,
                doc_type=doc.doc_type,
                original_filename=doc.original_filename,
                stored_filename=doc.stored_filename,
                content_type=doc.content_type,
                size_bytes=doc.size_bytes,
                is_verified=doc.is_verified,
                verifier_remark=doc.verifier_remark,
                uploaded_at=doc.uploaded_at,
            )
        )

    db.add(
        KYCHistory(
            kyc_id=kyc.id,
            action="admitted_from_submission",
            from_status=SubmissionStatus.under_review.value,
            to_status=KYCStatus.verified.value,
            actor_user_id=user.id,
            actor_name=user.email,
            remark=(
                f"Admitted from submission {record.reference_code}. {payload.remark}"
            ).strip(),
        )
    )

    record.status = SubmissionStatus.approved
    record.reviewed_by_id = user.id
    record.reviewed_at = now
    record.reviewer_remark = payload.remark
    record.created_employee_id = employee.id

    audit.log(
        db,
        user,
        "submission.approved",
        entity_type="submission",
        entity_id=record.id,
        summary=f"Admitted {record.full_name} from {record.reference_code} as {hrms_id}",
        detail={"employee_id": employee.id, "hrms_employee_id": hrms_id},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _admin_out(db, record)


@submissions_router.post(
    "/{submission_id}/documents/{doc_id}/verify", response_model=SubmissionDocumentOut
)
def verify_document(
    submission_id: int,
    doc_id: int,
    payload: SubmissionDecision,
    is_verified: bool = Query(True),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(SUBMISSION_REVIEW)),
):
    """Record the manual check of one attached document."""
    record = db.get(EmployeeSubmission, submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    _assert_submission_in_scope(db, user, record)
    doc = db.get(SubmissionDocument, doc_id)
    if doc is None or doc.submission_id != submission_id:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.is_verified = is_verified
    doc.verifier_remark = payload.remark
    db.commit()
    db.refresh(doc)
    return SubmissionDocumentOut.model_validate(doc)


router.include_router(submissions_router)
