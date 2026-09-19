"""Employee management (Admin/HR/Department Head) and self-service profile."""
import io
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import (
    client_ip,
    get_current_employee,
    get_current_user,
    require_perm,
)
from app.core.permissions import (
    EMPLOYEE_CREATE,
    EMPLOYEE_DELETE,
    EMPLOYEE_EDIT,
    EMPLOYEE_PROMOTE,
    EMPLOYEE_READ,
    PROFILE_EDIT_OWN,
    USER_RESET_PASSWORD,
)
from app.core.security import generate_temporary_password, hash_password
from app.models.models import (
    KYC,
    Designation,
    Employee,
    EmploymentStatus,
    KYCStatus,
    Location,
    OrgUnit,
    OrgUnitKind,
    PositionEventType,
    PositionHistory,
    Post,
    Role,
    User,
)
from app.schemas.schemas import (
    CredentialIssued,
    EmployeeCreate,
    EmployeeDetail,
    EmployeePhotoUpdate,
    EmployeeSummary,
    EmployeeUpdate,
    PositionHistoryOut,
    PromotionRequest,
    SelfProfileUpdate,
)
from app.services import storage
from app.services.employee_id import next_employee_id
from app.services import bulk_import
from app.services.hierarchy import direct_reports, reporting_chain
from app.services.retirement import calc_retirement_date
from app.services.org import (
    assert_employee_in_scope,
    department_scope_ids,
    nearest_of_kind,
    org_unit_descendant_ids as org_descendant_ids,
)
from app.services.serializers import employee_summary, org_path

router = APIRouter(prefix="/api/employees", tags=["Employees"])

PHOTO_SCOPE = "employee_photos"
PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _generate_id(db: Session, org_unit_id: int | None) -> str:
    unit = db.get(OrgUnit, org_unit_id) if org_unit_id else None
    return next_employee_id(db, unit)


def _id_establishment_short(db: Session, org_unit_id: int | None) -> str | None:
    """Nearest Establishment short_code above an org unit — used to detect
    whether a promotion crosses an establishment boundary."""
    if org_unit_id is None:
        return None
    unit = db.get(OrgUnit, org_unit_id)
    est = nearest_of_kind(db, unit, OrgUnitKind.establishment) if unit else None
    if est and (est.short_code or "").strip():
        return est.short_code.strip().upper()
    # Fall back to the department's own short code if there is no establishment.
    dept = nearest_of_kind(db, unit, OrgUnitKind.department) if unit else None
    if dept and (dept.short_code or "").strip():
        return dept.short_code.strip().upper()
    return None


def _require_scope(db: Session, user: User, emp: Employee) -> None:
    assert_employee_in_scope(db, user, emp)


def _detail(db: Session, emp: Employee) -> EmployeeDetail:
    base = employee_summary(db, emp)
    post_label = None
    if emp.post and emp.post.designation:
        post_label = f"{emp.post.designation.name} — {emp.post.org_unit.name}"

    history_rows = (
        db.query(PositionHistory)
        .filter(PositionHistory.employee_id == emp.id)
        .order_by(PositionHistory.effective_date, PositionHistory.created_at)
        .all()
    )
    history = [
        PositionHistoryOut(
            id=h.id,
            event_type=h.event_type,
            previous_designation=h.previous_designation.name
            if h.previous_designation
            else None,
            new_designation=h.new_designation.name if h.new_designation else None,
            previous_organization=h.previous_org_unit.name
            if h.previous_org_unit
            else None,
            new_organization=h.new_org_unit.name if h.new_org_unit else None,
            previous_employee_code=h.previous_employee_code,
            new_employee_code=h.new_employee_code,
            previous_pay_scale=h.previous_pay_scale,
            new_pay_scale=h.new_pay_scale,
            promotion_date=h.promotion_date,
            new_position_joining_date=h.new_position_joining_date,
            effective_date=h.effective_date,
            remarks=h.remarks,
            created_at=h.created_at,
        )
        for h in history_rows
    ]

    return EmployeeDetail(
        **base.model_dump(),
        gender=emp.gender,
        date_of_birth=emp.date_of_birth,
        date_of_joining=emp.date_of_joining,
        date_of_joining_aau_avfu=emp.date_of_joining_aau_avfu,
        date_of_joining_present_post=emp.date_of_joining_present_post,
        expected_date_of_retirement=emp.expected_date_of_retirement,
        post_id=emp.post_id,
        post_label=post_label,
        location_id=emp.location_id,
        pay_scale=emp.pay_scale,
        remarks=emp.remarks,
        kyc_status=emp.kyc.status if emp.kyc else KYCStatus.not_started,
        has_login=emp.user is not None,
        login_email=emp.user.email if emp.user else None,
        role_code=emp.user.role.code if emp.user and emp.user.role else None,
        user_is_active=emp.user.is_active if emp.user else None,
        direct_reports=[
            employee_summary(db, r, include_manager=False)
            for r in direct_reports(db, emp.id)
        ],
        reporting_chain=[
            employee_summary(db, m, include_manager=False)
            for m in reporting_chain(db, emp.id)
        ],
        history=history,
    )


# ---------------------------------------------------------------------------
# Self service — must be declared before /{employee_id}
# ---------------------------------------------------------------------------
@router.get("/me", response_model=EmployeeDetail)
def my_record(
    db: Session = Depends(get_db), emp: Employee = Depends(get_current_employee)
):
    return _detail(db, emp)


@router.put("/me", response_model=EmployeeDetail)
def update_my_record(
    payload: SelfProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee),
    user: User = Depends(get_current_user),
):
    """Employees may only change contact details.

    Designation, post, organisation and reporting authority are official
    HRMS data maintained by Admin/HR/Department Head.
    """
    if not user.has_permission(PROFILE_EDIT_OWN):
        raise HTTPException(status_code=403, detail="Not permitted")
    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(emp, k) for k in changes}
    for key, value in changes.items():
        setattr(emp, key, value)
    audit.log(
        db,
        user,
        "employee.self_update",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"{emp.full_name} updated their own contact details",
        detail=audit.diff(before, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _detail(db, emp)


# ---------------------------------------------------------------------------
# Admin/HR/Department Head employee management
# ---------------------------------------------------------------------------
@router.get("", response_model=list[EmployeeSummary])
def list_employees(
    q: str = "",
    org_unit_id: int | None = None,
    # Accepted for frontend compatibility; all resolve to an org-unit subtree.
    college_id: int | None = None,
    department_id: int | None = None,
    establishment_id: int | None = None,
    organization_id: int | None = None,
    include_subtree: bool = True,
    location_id: int | None = None,
    designation_id: int | None = None,
    employment_status: EmploymentStatus | None = None,
    include_inactive: bool = False,
    limit: int = Query(200, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_READ)),
):
    query = db.query(Employee)

    unit_filter = (
        org_unit_id
        or organization_id
        or establishment_id
        or department_id
        or college_id
    )

    scope = department_scope_ids(db, user)
    if scope is not None:
        if unit_filter is not None:
            requested = (
                org_descendant_ids(db, unit_filter)
                if include_subtree
                else {unit_filter}
            )
            ids = requested & scope
        else:
            ids = scope
        query = query.filter(Employee.org_unit_id.in_(ids))
    elif unit_filter is not None:
        ids = (
            org_descendant_ids(db, unit_filter)
            if include_subtree
            else {unit_filter}
        )
        query = query.filter(Employee.org_unit_id.in_(ids))

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Employee.full_name.ilike(like),
                Employee.hrms_employee_id.ilike(like),
                Employee.official_email.ilike(like),
            )
        )
    if location_id is not None:
        query = query.filter(Employee.location_id == location_id)
    if designation_id is not None:
        query = query.filter(Employee.designation_id == designation_id)
    if employment_status is not None:
        query = query.filter(Employee.employment_status == employment_status)
    if not include_inactive:
        query = query.filter(Employee.is_active.is_(True))

    rows = query.order_by(Employee.full_name).offset(offset).limit(limit).all()
    return [employee_summary(db, e) for e in rows]


@router.post("", response_model=CredentialIssued, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_CREATE)),
):
    """Create the employee record, and a login only if one was asked for.

    Ordinary employees do not sign in. When a login *is* created — for
    another Administrator, HR user or Department Head — the temporary
    password is returned exactly once; it is stored only as a bcrypt hash
    and cannot be read back afterwards.
    """
    scope = department_scope_ids(db, user)
    if scope is not None and (
        payload.org_unit_id is None or payload.org_unit_id not in scope
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only create employees within the department you manage",
        )

    hrms_id = (
        payload.hrms_employee_id or ""
    ).strip() or _generate_id(db, payload.org_unit_id)
    if db.query(Employee).filter(Employee.hrms_employee_id == hrms_id).first():
        raise HTTPException(
            status_code=409, detail=f"HRMS Employee ID {hrms_id} is already in use"
        )

    for model, value, label in (
        (OrgUnit, payload.org_unit_id, "Office / org unit"),
        (Location, payload.location_id, "Campus"),
        (Designation, payload.designation_id, "Designation"),
        (Post, payload.post_id, "Post"),
    ):
        if value is not None and db.get(model, value) is None:
            raise HTTPException(status_code=400, detail=f"{label} not found")

    designation = (
        db.get(Designation, payload.designation_id) if payload.designation_id else None
    )
    expected_retirement = payload.expected_date_of_retirement or calc_retirement_date(
        payload.date_of_birth, designation.rank_level if designation else None
    )

    emp = Employee(
        hrms_employee_id=hrms_id,
        full_name=payload.full_name.strip(),
        gender=payload.gender,
        date_of_birth=payload.date_of_birth,
        date_of_joining_aau_avfu=payload.date_of_joining_aau_avfu,
        date_of_joining_present_post=payload.date_of_joining_present_post,
        expected_date_of_retirement=expected_retirement,
        official_email=payload.official_email.strip().lower(),
        phone=payload.phone,
        photo_url=payload.photo_url,
        org_unit_id=payload.org_unit_id,
        location_id=payload.location_id,
        designation_id=payload.designation_id,
        post_id=payload.post_id,
        pay_scale=payload.pay_scale,
        date_of_joining=payload.date_of_joining,
        employment_status=payload.employment_status,
        remarks=payload.remarks,
    )
    db.add(emp)
    db.flush()

    db.add(KYC(employee_id=emp.id, status=KYCStatus.not_started))
    db.add(
        PositionHistory(
            employee_id=emp.id,
            event_type=PositionEventType.joining,
            new_designation_id=payload.designation_id,
            new_org_unit_id=payload.org_unit_id,
            new_employee_code=hrms_id,
            new_pay_scale=payload.pay_scale,
            effective_date=payload.date_of_joining or date.today(),
            new_position_joining_date=payload.date_of_joining,
            remarks="Joined AVFU",
            created_by_id=user.id,
        )
    )

    temp_password = ""
    login_email = ""
    if payload.create_login:
        login_email = (
            payload.login_email or payload.official_email or ""
        ).strip().lower()
        if not login_email:
            raise HTTPException(
                status_code=400,
                detail="A login email is required to create an account",
            )
        if db.query(User).filter(User.email == login_email).first():
            raise HTTPException(
                status_code=409, detail="That login email is already registered"
            )
        role = db.query(Role).filter(Role.code == payload.role_code).first()
        if role is None:
            raise HTTPException(
                status_code=400, detail=f"Unknown role '{payload.role_code}'"
            )

        temp_password = payload.initial_password or generate_temporary_password()
        account = User(
            email=login_email,
            hashed_password=hash_password(temp_password),
            role_id=role.id,
            is_active=True,
            must_change_password=True,
            created_by_id=user.id,
        )
        db.add(account)
        db.flush()
        emp.user_id = account.id

    audit.log(
        db,
        user,
        "employee.create",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"Created employee {emp.full_name} ({hrms_id})",
        detail={"login_created": bool(payload.create_login), "login_email": login_email},
        ip=client_ip(request),
    )
    db.commit()

    return CredentialIssued(
        employee_id=emp.id,
        hrms_employee_id=hrms_id,
        login_email=login_email,
        temporary_password=temp_password,
    )


# ---------------------------------------------------------------------------
# Bulk import — onboarding current employees in one pass
# ---------------------------------------------------------------------------
@router.get("/bulk-import/template")
def bulk_import_template(user: User = Depends(require_perm(EMPLOYEE_CREATE))):
    wb = bulk_import.build_template()
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="employee_bulk_import_template.xlsx"'
        },
    )


@router.post("/bulk-import")
def bulk_import_employees(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_CREATE)),
):
    """Create many current employees at once from an uploaded .xlsx sheet.

    Each row becomes its own transaction-safe attempt: a bad row is reported
    and skipped rather than aborting the whole sheet. No login accounts are
    created here; HR issues those individually afterwards if needed.
    """
    contents = file.file.read()
    try:
        rows = bulk_import.parse_rows(contents)
    except bulk_import.RowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not rows:
        raise HTTPException(status_code=400, detail="The sheet has no data rows")

    scope = department_scope_ids(db, user)

    created = 0
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            emp = bulk_import.create_employee_from_row(db, row, i, _generate_id)
            if scope is not None and emp.org_unit_id not in scope:
                raise bulk_import.RowError(
                    f"Row {i}: that org unit is outside the department you manage"
                )
            db.add(emp)
            db.flush()
            db.add(KYC(employee_id=emp.id, status=KYCStatus.not_started))
            db.add(
                PositionHistory(
                    employee_id=emp.id,
                    event_type=PositionEventType.joining,
                    new_designation_id=emp.designation_id,
                    new_org_unit_id=emp.org_unit_id,
                    new_employee_code=emp.hrms_employee_id,
                    new_pay_scale=emp.pay_scale,
                    effective_date=emp.date_of_joining or date.today(),
                    new_position_joining_date=emp.date_of_joining,
                    remarks="Bulk-imported as a current employee",
                    created_by_id=user.id,
                )
            )
            created += 1
        except bulk_import.RowError as exc:
            db.rollback()
            errors.append(str(exc))

    if created:
        audit.log(
            db,
            user,
            "employee.bulk_import",
            entity_type="employee",
            entity_id=0,
            summary=f"Bulk-imported {created} employee(s)",
            detail={"created": created, "failed": len(errors)},
            ip=client_ip(request),
        )
        db.commit()

    return {"created": created, "failed": len(errors), "errors": errors}


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_READ)),
):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)
    return _detail(db, emp)


@router.put("/{employee_id}", response_model=EmployeeDetail)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_EDIT)),
):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)

    changes = payload.model_dump(exclude_unset=True)

    scope = department_scope_ids(db, user)
    if scope is not None and "org_unit_id" in changes:
        if changes["org_unit_id"] not in scope:
            raise HTTPException(
                status_code=403,
                detail="You cannot move an employee outside the department you manage",
            )

    for field, model, label in (
        ("org_unit_id", OrgUnit, "Office / org unit"),
        ("location_id", Location, "Campus"),
        ("designation_id", Designation, "Designation"),
        ("post_id", Post, "Post"),
    ):
        value = changes.get(field)
        if value is not None and db.get(model, value) is None:
            raise HTTPException(status_code=400, detail=f"{label} not found")

    if (
        "date_of_birth" in changes or "designation_id" in changes
    ) and "expected_date_of_retirement" not in changes:
        dob = changes.get("date_of_birth", emp.date_of_birth)
        designation_id = changes.get("designation_id", emp.designation_id)
        designation = db.get(Designation, designation_id) if designation_id else None
        changes["expected_date_of_retirement"] = calc_retirement_date(
            dob, designation.rank_level if designation else None
        )

    before = {k: getattr(emp, k) for k in changes}
    for key, value in changes.items():
        setattr(emp, key, value)
    audit.log(
        db,
        user,
        "employee.update",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"Updated employee {emp.full_name} ({emp.hrms_employee_id})",
        detail=audit.diff(before, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _detail(db, emp)


@router.post("/{employee_id}/photo", response_model=EmployeeDetail)
def upload_photo(
    employee_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_EDIT)),
):
    """Add or replace an employee's photo. Admin/HR/Department Head."""
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)

    if file.content_type not in PHOTO_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG or WebP images are accepted"
        )
    stored_name, _ = storage.save_upload(PHOTO_SCOPE, emp.id, file)
    emp.photo_url = f"/api/employees/{emp.id}/photo/{stored_name}"

    audit.log(
        db,
        user,
        "employee.photo_update",
        entity_type="employee",
        entity_id=emp.id,
        summary=f"Updated photo for {emp.full_name} ({emp.hrms_employee_id})",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _detail(db, emp)


_PHOTO_CONTENT_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.get("/{employee_id}/photo/{stored_filename}")
def get_photo(
    employee_id: int,
    stored_filename: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    suffix = "." + stored_filename.rsplit(".", 1)[-1].lower() if "." in stored_filename else ""
    content_type = _PHOTO_CONTENT_BY_SUFFIX.get(suffix, "application/octet-stream")
    return storage.send_file(
        PHOTO_SCOPE, employee_id, stored_filename, content_type, stored_filename
    )


@router.get("/{employee_id}/history", response_model=list[PositionHistoryOut])
def get_history(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_READ)),
):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)
    return _detail(db, emp).history


@router.post("/{employee_id}/promote", response_model=EmployeeDetail)
def promote_employee(
    employee_id: int,
    payload: PromotionRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_PROMOTE)),
):
    """Promote an employee, always preserving history.

    If the new organisation belongs to a different Establishment than the
    employee's current one, a new Employee ID is generated using the new
    Establishment's Short Form and the previous ID is kept in the
    employee's history. If the Establishment is unchanged, the Employee ID
    stays the same.
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)

    new_unit_id = payload.new_org_unit_id or emp.org_unit_id
    scope = department_scope_ids(db, user)
    if scope is not None and new_unit_id not in scope:
        raise HTTPException(
            status_code=403,
            detail="You cannot promote an employee outside the department you manage",
        )
    if payload.new_org_unit_id is not None and db.get(
        OrgUnit, payload.new_org_unit_id
    ) is None:
        raise HTTPException(status_code=400, detail="New office / org unit not found")
    if payload.new_designation_id is not None and db.get(
        Designation, payload.new_designation_id
    ) is None:
        raise HTTPException(status_code=400, detail="New designation not found")
    if payload.new_post_id is not None and db.get(Post, payload.new_post_id) is None:
        raise HTTPException(status_code=400, detail="New post not found")

    previous_est = _id_establishment_short(db, emp.org_unit_id)
    new_est = _id_establishment_short(db, new_unit_id)
    establishment_changed = (
        previous_est is not None and new_est is not None and previous_est != new_est
    )

    previous_code = emp.hrms_employee_id
    new_code = previous_code
    if establishment_changed:
        new_code = _generate_id(db, new_unit_id)

    event = PositionHistory(
        employee_id=emp.id,
        event_type=(
            PositionEventType.establishment_change
            if establishment_changed
            else PositionEventType.promotion
        ),
        previous_designation_id=emp.designation_id,
        new_designation_id=payload.new_designation_id or emp.designation_id,
        previous_org_unit_id=emp.org_unit_id,
        new_org_unit_id=new_unit_id,
        previous_employee_code=previous_code,
        new_employee_code=new_code,
        previous_pay_scale=emp.pay_scale,
        new_pay_scale=payload.new_pay_scale if payload.new_pay_scale is not None else emp.pay_scale,
        promotion_date=payload.promotion_date or date.today(),
        new_position_joining_date=payload.new_position_joining_date,
        effective_date=payload.promotion_date
        or payload.new_position_joining_date
        or date.today(),
        remarks=payload.remarks,
        created_by_id=user.id,
    )
    db.add(event)

    # A dedicated ID-change event so the timeline shows the old -> new ID
    # explicitly (Section 9 of the requirement).
    if establishment_changed and new_code != previous_code:
        db.add(
            PositionHistory(
                employee_id=emp.id,
                event_type=PositionEventType.employee_id_change,
                previous_employee_code=previous_code,
                new_employee_code=new_code,
                previous_org_unit_id=emp.org_unit_id,
                new_org_unit_id=new_unit_id,
                effective_date=event.effective_date,
                remarks="Employee ID changed on establishment change",
                created_by_id=user.id,
            )
        )

    before = {
        "designation_id": emp.designation_id,
        "org_unit_id": emp.org_unit_id,
        "post_id": emp.post_id,
        "pay_scale": emp.pay_scale,
        "hrms_employee_id": emp.hrms_employee_id,
    }
    if payload.new_designation_id is not None:
        emp.designation_id = payload.new_designation_id
    if payload.new_org_unit_id is not None:
        emp.org_unit_id = payload.new_org_unit_id
    if payload.new_post_id is not None:
        emp.post_id = payload.new_post_id
    if payload.new_pay_scale is not None:
        emp.pay_scale = payload.new_pay_scale
    if new_code != previous_code:
        emp.hrms_employee_id = new_code

    audit.log(
        db,
        user,
        "employee.promote",
        entity_type="employee",
        entity_id=emp.id,
        summary=(
            f"Promoted {emp.full_name}: {before['hrms_employee_id']} -> {new_code}"
            if new_code != previous_code
            else f"Promoted {emp.full_name} ({emp.hrms_employee_id})"
        ),
        detail=audit.diff(
            before,
            {
                "designation_id": emp.designation_id,
                "org_unit_id": emp.org_unit_id,
                "post_id": emp.post_id,
                "pay_scale": emp.pay_scale,
                "hrms_employee_id": emp.hrms_employee_id,
            },
        ),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _detail(db, emp)


@router.post("/{employee_id}/activation", response_model=EmployeeDetail)
def set_activation(
    employee_id: int,
    is_active: bool,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_DELETE)),
):
    """Activate or deactivate an employee together with their login.

    This never deletes the employee, their documents or their history —
    retired or departed staff simply stop being treated as active.
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)

    emp.is_active = is_active
    emp.employment_status = (
        EmploymentStatus.active if is_active else EmploymentStatus.inactive
    )
    if emp.user:
        emp.user.is_active = is_active
    audit.log(
        db,
        user,
        "employee.activate" if is_active else "employee.deactivate",
        entity_type="employee",
        entity_id=emp.id,
        summary=(
            f"{'Activated' if is_active else 'Deactivated'} "
            f"{emp.full_name} ({emp.hrms_employee_id})"
        ),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _detail(db, emp)


@router.post("/{employee_id}/credentials", response_model=CredentialIssued)
def issue_credentials(
    employee_id: int,
    request: Request,
    login_email: str | None = None,
    role_code: str = "hr_admin",
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(EMPLOYEE_CREATE, USER_RESET_PASSWORD)),
):
    """Create a login for an employee who has none, or reset an existing one.

    Admin never sees the employee's current password — this replaces it with
    a freshly generated temporary one.
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _require_scope(db, user, emp)

    temp_password = generate_temporary_password()

    if emp.user is None:
        email = (login_email or emp.official_email or "").strip().lower()
        if not email:
            raise HTTPException(
                status_code=400, detail="A login email is required for this employee"
            )
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=409, detail="That login email is already registered"
            )
        role = db.query(Role).filter(Role.code == role_code).first()
        if role is None:
            raise HTTPException(status_code=400, detail=f"Unknown role '{role_code}'")
        account = User(
            email=email,
            hashed_password=hash_password(temp_password),
            role_id=role.id,
            must_change_password=True,
            created_by_id=user.id,
        )
        db.add(account)
        db.flush()
        emp.user_id = account.id
        action = "user.create"
    else:
        account = emp.user
        account.hashed_password = hash_password(temp_password)
        account.must_change_password = True
        account.password_changed_at = datetime.now(timezone.utc)
        account.reset_token_hash = ""
        account.reset_token_expires_at = None
        action = "user.password_reset_by_admin"

    audit.log(
        db,
        user,
        action,
        entity_type="employee",
        entity_id=emp.id,
        summary=f"Issued temporary credentials for {emp.full_name} ({emp.hrms_employee_id})",
        ip=client_ip(request),
    )
    db.commit()

    return CredentialIssued(
        employee_id=emp.id,
        hrms_employee_id=emp.hrms_employee_id,
        login_email=account.email,
        temporary_password=temp_password,
    )
