"""Employee KYC records, maintained and verified by HR.

Employees have no login, so there is no self-service surface here. Documents
arrive through the public submission form (``app/routers/public.py``) and are
carried onto the employee's KYC record when HR admits them. HR can also
amend a record and re-verify it afterwards.
"""
from datetime import date, datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, require_perm
from app.core.permissions import KYC_VERIFY
from app.models.models import (
    KYC,
    Employee,
    KYCDocument,
    KYCHistory,
    KYCStatus,
    User,
)
from app.schemas.schemas import (
    KYCDecision,
    KYCDocumentOut,
    KYCDocumentVerify,
    KYCHistoryOut,
    KYCInfoUpdate,
    KYCOut,
)
from app.services import storage
from app.services.org import department_scope_ids, org_path
from app.services.retirement import calc_retirement_date

router = APIRouter(prefix="/api/kyc", tags=["KYC"])

SCOPE = "kyc"

# HR may amend a record in any state except while it is already verified;
# re-verification is an explicit action.
DECIDABLE = {
    KYCStatus.not_started,
    KYCStatus.draft,
    KYCStatus.submitted,
    KYCStatus.under_verification,
    KYCStatus.resubmission_required,
    KYCStatus.rejected,
}


def _get(db: Session, kyc_id: int, user: User) -> KYC:
    record = db.get(KYC, kyc_id)
    if record is None:
        raise HTTPException(status_code=404, detail="KYC record not found")
    scope = department_scope_ids(db, user)
    if scope is not None and (record.employee is None or record.employee.org_unit_id not in scope):
        raise HTTPException(status_code=403, detail="This employee is outside the department you manage")
    return record


def _history(
    db: Session,
    record: KYC,
    action: str,
    from_status: KYCStatus,
    to_status: KYCStatus,
    actor: User,
    remark: str = "",
) -> None:
    db.add(
        KYCHistory(
            kyc_id=record.id,
            action=action,
            from_status=from_status.value,
            to_status=to_status.value,
            actor_user_id=actor.id,
            actor_name=actor.email,
            remark=remark,
        )
    )


def _kyc_out(db: Session, record: KYC) -> KYCOut:
    emp = record.employee
    return KYCOut(
        **{
            field: getattr(record, field)
            for field in (
                "id",
                "employee_id",
                "status",
                "father_name",
                "mother_name",
                "date_of_birth",
                "date_of_joining_aau_avfu",
                "date_of_joining_present_post",
                "expected_date_of_retirement",
                "gender",
                "blood_group",
                "marital_status",
                "nationality",
                "category",
                "aadhaar_number",
                "pan_number",
                "personal_email",
                "contact_phone",
                "emergency_contact_name",
                "emergency_contact_phone",
                "permanent_address",
                "present_address",
                "bank_name",
                "bank_account_number",
                "bank_ifsc",
                "submitted_at",
                "verified_at",
                "verifier_remark",
            )
        },
        employee_name=emp.full_name if emp else "",
        hrms_employee_id=emp.hrms_employee_id if emp else "",
        organization=org_path(db, emp.org_unit) if emp else None,
        designation=emp.designation.name if emp and emp.designation else None,
        verified_by_name=record.verified_by.email if record.verified_by else None,
        documents=[KYCDocumentOut.model_validate(d) for d in record.documents],
        history=[KYCHistoryOut.model_validate(h) for h in record.history],
        can_edit=record.status != KYCStatus.verified,
    )


@router.get("/document-types", response_model=list[str])
def document_types(user: User = Depends(require_perm(KYC_VERIFY))):
    return storage.DOCUMENT_TYPES


@router.get("", response_model=list[KYCOut])
def list_kyc(
    kyc_status: KYCStatus | None = None,
    q: str = "",
    limit: int = Query(300, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    query = db.query(KYC).join(Employee, KYC.employee_id == Employee.id)
    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(Employee.org_unit_id.in_(scope))
    if kyc_status is not None:
        query = query.filter(KYC.status == kyc_status)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            Employee.full_name.ilike(like) | Employee.hrms_employee_id.ilike(like)
        )
    rows = (
        query.order_by(Employee.full_name).offset(offset).limit(limit).all()
    )
    return [_kyc_out(db, r) for r in rows]


@router.get("/by-employee/{employee_id}", response_model=KYCOut)
def kyc_for_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    record = db.query(KYC).filter(KYC.employee_id == employee_id).first()
    scope = department_scope_ids(db, user)
    employee = db.get(Employee, employee_id)
    if scope is not None and (employee is None or employee.org_unit_id not in scope):
        raise HTTPException(status_code=403, detail="This employee is outside the department you manage")
    if record is None:
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        record = KYC(employee_id=employee_id, status=KYCStatus.not_started)
        db.add(record)
        db.commit()
        db.refresh(record)
    return _kyc_out(db, record)


@router.get("/{kyc_id}", response_model=KYCOut)
def get_kyc(
    kyc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    return _kyc_out(db, _get(db, kyc_id, user))


@router.put("/{kyc_id}", response_model=KYCOut)
def update_kyc(
    kyc_id: int,
    payload: KYCInfoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    """HR maintains the record on the employee's behalf."""
    record = _get(db, kyc_id, user)
    changes = payload.model_dump(exclude_unset=True)
    if "date_of_birth" in changes and "expected_date_of_retirement" not in changes:
        designation = record.employee.designation if record.employee else None
        changes["expected_date_of_retirement"] = calc_retirement_date(
            changes["date_of_birth"],
            designation.rank_level if designation else None,
        )
    before = {k: getattr(record, k) for k in changes}
    for key, value in changes.items():
        setattr(record, key, value)
    audit.log(
        db,
        user,
        "kyc.update",
        entity_type="kyc",
        entity_id=record.id,
        summary=(
            f"Updated KYC for "
            f"{record.employee.full_name if record.employee else record.employee_id}"
        ),
        detail=audit.diff(before, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _kyc_out(db, record)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@router.post(
    "/{kyc_id}/documents",
    response_model=KYCDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    kyc_id: int,
    request: Request,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    record = _get(db, kyc_id, user)
    stored_name, contents = storage.save_upload(SCOPE, record.id, file)
    doc = KYCDocument(
        kyc_id=record.id,
        doc_type=doc_type,
        original_filename=file.filename or stored_name,
        stored_filename=stored_name,
        content_type=file.content_type or "",
        size_bytes=len(contents),
    )
    db.add(doc)
    audit.log(
        db,
        user,
        "kyc.document_upload",
        entity_type="kyc",
        entity_id=record.id,
        summary=f"Added a '{doc_type}' document",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(doc)
    return KYCDocumentOut.model_validate(doc)


@router.get("/{kyc_id}/documents/{doc_id}/file")
def download_document(
    kyc_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    _get(db, kyc_id, user)  # 403s if this KYC record is outside the caller's scope
    doc = db.get(KYCDocument, doc_id)
    if doc is None or doc.kyc_id != kyc_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return storage.send_file(
        SCOPE, kyc_id, doc.stored_filename, doc.content_type, doc.original_filename
    )


@router.delete("/{kyc_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    kyc_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    _get(db, kyc_id, user)  # 403s if this KYC record is outside the caller's scope
    doc = db.get(KYCDocument, doc_id)
    if doc is None or doc.kyc_id != kyc_id:
        raise HTTPException(status_code=404, detail="Document not found")
    storage.delete_file(SCOPE, kyc_id, doc.stored_filename)
    db.delete(doc)
    db.commit()


@router.post("/{kyc_id}/documents/{doc_id}/verify", response_model=KYCDocumentOut)
def verify_document(
    kyc_id: int,
    doc_id: int,
    payload: KYCDocumentVerify,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    _get(db, kyc_id, user)  # 403s if this KYC record is outside the caller's scope
    doc = db.get(KYCDocument, doc_id)
    if doc is None or doc.kyc_id != kyc_id:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.is_verified = payload.is_verified
    doc.verifier_remark = payload.remark
    db.commit()
    db.refresh(doc)
    return KYCDocumentOut.model_validate(doc)


# ---------------------------------------------------------------------------
# Manual decisions — nothing here happens automatically
# ---------------------------------------------------------------------------
def _decide(
    db: Session,
    request: Request,
    kyc_id: int,
    user: User,
    to_status: KYCStatus,
    action: str,
    remark: str,
) -> KYCOut:
    record = _get(db, kyc_id, user)
    if record.status == to_status:
        raise HTTPException(
            status_code=400, detail=f"This record is already '{to_status.value}'"
        )
    previous = record.status
    record.status = to_status
    record.verifier_remark = remark
    record.verified_by_id = user.id
    record.verified_at = datetime.now(timezone.utc)

    _history(db, record, action, previous, to_status, user, remark)
    audit.log(
        db,
        user,
        f"kyc.{action}",
        entity_type="kyc",
        entity_id=record.id,
        summary=(
            f"KYC for "
            f"{record.employee.full_name if record.employee else record.employee_id} "
            f"moved {previous.value} -> {to_status.value}"
        ),
        detail={"remark": remark},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(record)
    return _kyc_out(db, record)


@router.post("/{kyc_id}/start-verification", response_model=KYCOut)
def start_verification(
    kyc_id: int,
    payload: KYCDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    return _decide(
        db, request, kyc_id, user, KYCStatus.under_verification,
        "start_verification", payload.remark,
    )


@router.post("/{kyc_id}/approve", response_model=KYCOut)
def approve_kyc(
    kyc_id: int,
    payload: KYCDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    """Manual approval — there is no automatic path to this state."""
    record = _get(db, kyc_id, user)
    if not record.documents:
        raise HTTPException(
            status_code=400,
            detail="Cannot verify a record with no supporting documents",
        )
    return _decide(
        db, request, kyc_id, user, KYCStatus.verified, "approve", payload.remark
    )


@router.post("/{kyc_id}/reject", response_model=KYCOut)
def reject_kyc(
    kyc_id: int,
    payload: KYCDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    if not payload.remark.strip():
        raise HTTPException(
            status_code=400, detail="A reason is required when rejecting KYC"
        )
    return _decide(
        db, request, kyc_id, user, KYCStatus.rejected, "reject", payload.remark
    )


@router.post("/{kyc_id}/request-resubmission", response_model=KYCOut)
def request_resubmission(
    kyc_id: int,
    payload: KYCDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(KYC_VERIFY)),
):
    if not payload.remark.strip():
        raise HTTPException(
            status_code=400,
            detail="Explain what must be corrected before resubmission",
        )
    return _decide(
        db, request, kyc_id, user, KYCStatus.resubmission_required,
        "request_resubmission", payload.remark,
    )
