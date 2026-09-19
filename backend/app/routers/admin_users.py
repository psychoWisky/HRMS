"""User accounts, roles, permissions and audit log."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, require_perm
from app.core.permissions import (
    AUDIT_READ,
    ROLE_MANAGE,
    USER_MANAGE,
    USER_RESET_PASSWORD,
)
from app.core.security import generate_temporary_password, hash_password
from app.models.models import (
    AuditLog,
    Employee,
    Permission,
    Role,
    User,
)
from app.models.models import OrgUnit
from app.schemas.schemas import (
    AuditLogOut,
    CredentialIssued,
    PermissionOut,
    PersonOut,
    PersonRoleUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserActiveUpdate,
    UserScopeUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["Users, Roles & System"])


def _person_out(emp: Employee) -> PersonOut:
    user = emp.user
    return PersonOut(
        employee_id=emp.id,
        employee_name=emp.full_name,
        hrms_employee_id=emp.hrms_employee_id,
        designation=emp.designation.name if emp.designation else None,
        organization=emp.org_unit.name if emp.org_unit else None,
        has_login=user is not None,
        user_id=user.id if user else None,
        login_email=user.email if user else None,
        role_code=user.role.code if user and user.role else "",
        role_name=user.role.name if user and user.role else "",
        is_active=user.is_active if user else True,
        must_change_password=user.must_change_password if user else False,
        last_login_at=user.last_login_at if user else None,
        managed_org_unit_id=user.managed_org_unit_id if user else None,
        managed_org_unit_name=(
            user.managed_org_unit.name if user and user.managed_org_unit else None
        ),
    )


def _role_out(db: Session, role: Role) -> RoleOut:
    count = db.query(func.count(User.id)).filter(User.role_id == role.id).scalar()
    return RoleOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        permissions=role.permission_codes,
        user_count=count or 0,
        is_hidden=role.is_hidden,
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[PersonOut])
def list_users(
    q: str = "",
    role_code: str | None = None,
    include_inactive: bool = True,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(USER_MANAGE)),
):
    """Every employee — Admin/HR decide who gets what access from here.

    Someone with no login yet still appears, with ``has_login=false``;
    assigning them a role (``PUT /users/{employee_id}/role``) creates one.
    """
    query = db.query(Employee).filter(Employee.is_active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        query = query.outerjoin(User, Employee.user_id == User.id).filter(
            Employee.full_name.ilike(term)
            | Employee.hrms_employee_id.ilike(term)
            | User.email.ilike(term)
        )
    if role_code:
        query = query.join(User, Employee.user_id == User.id).join(Role).filter(
            Role.code == role_code
        )
    if not include_inactive:
        query = query.outerjoin(User, Employee.user_id == User.id).filter(
            (Employee.user_id.is_(None)) | (User.is_active.is_(True))
        )
    employees = query.order_by(Employee.full_name).all()
    return [_person_out(e) for e in employees]


@router.put("/users/{employee_id}/role", response_model=PersonOut)
def change_user_role(
    employee_id: int,
    payload: PersonRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(USER_MANAGE)),
):
    """Assign a role to any employee, creating their login if they don't
    have one yet. Admin/HR decide who gets HR, Department Head or Admin
    access — nobody needs to already have a login for this to work."""
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    role = db.query(Role).filter(Role.code == payload.role_code).first()
    if role is None:
        raise HTTPException(status_code=400, detail="Unknown role")

    target = emp.user
    if target is not None and target.id == actor.id and role.code != actor.role.code:
        raise HTTPException(status_code=400, detail="You cannot change your own role")

    previous = target.role.code if target and target.role else ""

    if target is None:
        email = (payload.login_email or emp.official_email or "").strip().lower()
        if not email:
            raise HTTPException(
                status_code=400,
                detail="A login email is required to give this employee a role "
                "(their official email is blank)",
            )
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=409, detail="That login email is already registered"
            )
        target = User(
            email=email,
            hashed_password=hash_password(generate_temporary_password()),
            role_id=role.id,
            must_change_password=True,
            created_by_id=actor.id,
        )
        db.add(target)
        db.flush()
        emp.user_id = target.id
    else:
        target.role_id = role.id

    if role.code != "department_head":
        # Never leave a stale managed-department assignment on an account
        # that is no longer a Department Head.
        target.managed_org_unit_id = None

    audit.log(
        db,
        actor,
        "user.role_change",
        entity_type="user",
        entity_id=target.id,
        summary=f"Changed role of {emp.full_name} ({target.email}): {previous or 'none'} -> {role.code}",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    out = _person_out(emp)
    if role.code == "department_head" and not target.managed_org_unit_id:
        # Deny-by-default until a department is assigned (see
        # app.services.org.department_scope_ids) — flag it back to the
        # caller so the UI can prompt for it immediately, rather than
        # leaving a silently-unscoped account.
        out.needs_department_assignment = True
    return out


@router.put("/users/{employee_id}/activation", response_model=PersonOut)
def set_user_active(
    employee_id: int,
    payload: UserActiveUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(USER_MANAGE)),
):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    target = emp.user
    if target is None:
        raise HTTPException(status_code=400, detail="This employee has no login to activate/deactivate")
    if target.id == actor.id and not payload.is_active:
        raise HTTPException(
            status_code=400, detail="You cannot deactivate your own account"
        )
    target.is_active = payload.is_active
    audit.log(
        db,
        actor,
        "user.activate" if payload.is_active else "user.deactivate",
        entity_type="user",
        entity_id=target.id,
        summary=f"{'Activated' if payload.is_active else 'Deactivated'} {target.email}",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _person_out(emp)


@router.post("/users/{employee_id}/reset-password", response_model=CredentialIssued)
def admin_reset_password(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(USER_RESET_PASSWORD)),
):
    """Replace a user's password with a fresh temporary one.

    The existing password is never readable — it is overwritten, not revealed.
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    target = emp.user
    if target is None:
        raise HTTPException(status_code=400, detail="This employee has no login yet")

    temp_password = generate_temporary_password()
    target.hashed_password = hash_password(temp_password)
    target.must_change_password = True
    target.reset_token_hash = ""
    target.reset_token_expires_at = None

    audit.log(
        db,
        actor,
        "user.password_reset_by_admin",
        entity_type="user",
        entity_id=target.id,
        summary=f"Reset password for {target.email}",
        ip=client_ip(request),
    )
    db.commit()

    return CredentialIssued(
        employee_id=emp.id,
        hrms_employee_id=emp.hrms_employee_id,
        login_email=target.email,
        temporary_password=temp_password,
    )


# ---------------------------------------------------------------------------
# Roles & permissions
# ---------------------------------------------------------------------------
@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db), actor: User = Depends(require_perm(ROLE_MANAGE))
):
    return [
        PermissionOut.model_validate(p)
        for p in db.query(Permission).order_by(Permission.group, Permission.code).all()
    ]


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_db), actor: User = Depends(require_perm(USER_MANAGE))
):
    """Every assignable role — the hidden Super Admin role never appears here."""
    rows = (
        db.query(Role)
        .filter(Role.is_hidden.is_(False))
        .order_by(Role.name)
        .all()
    )
    return [_role_out(db, r) for r in rows]


@router.put("/users/{employee_id}/scope", response_model=PersonOut)
def set_user_scope(
    employee_id: int,
    payload: UserScopeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(USER_MANAGE)),
):
    """Assign the one department a Department Head account may manage."""
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    target = emp.user
    if target is None:
        raise HTTPException(status_code=400, detail="This employee has no login yet")
    if payload.managed_org_unit_id is not None and db.get(
        OrgUnit, payload.managed_org_unit_id
    ) is None:
        raise HTTPException(status_code=400, detail="Org unit not found")
    previous = target.managed_org_unit_id
    target.managed_org_unit_id = payload.managed_org_unit_id
    audit.log(
        db,
        actor,
        "user.scope_change",
        entity_type="user",
        entity_id=target.id,
        summary=f"Changed managed department for {target.email}",
        detail={"previous": previous, "new": payload.managed_org_unit_id},
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(emp)
    return _person_out(emp)


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(ROLE_MANAGE)),
):
    if db.query(Role).filter(Role.code == payload.code).first():
        raise HTTPException(status_code=409, detail="That role code already exists")
    role = Role(code=payload.code, name=payload.name, description=payload.description)
    role.permissions = (
        db.query(Permission).filter(Permission.code.in_(payload.permissions)).all()
    )
    db.add(role)
    db.flush()
    audit.log(
        db,
        actor,
        "role.create",
        entity_type="role",
        entity_id=role.id,
        summary=f"Created role '{role.name}'",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(ROLE_MANAGE)),
):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    changes = payload.model_dump(exclude_unset=True)
    permissions = changes.pop("permissions", None)
    for key, value in changes.items():
        setattr(role, key, value)
    if permissions is not None:
        role.permissions = (
            db.query(Permission).filter(Permission.code.in_(permissions)).all()
        )
    audit.log(
        db,
        actor,
        "role.update",
        entity_type="role",
        entity_id=role.id,
        summary=f"Updated role '{role.name}'",
        detail={"permissions": permissions} if permissions is not None else None,
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(ROLE_MANAGE)),
):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="System roles cannot be deleted")
    in_use = db.query(func.count(User.id)).filter(User.role_id == role.id).scalar()
    if in_use:
        raise HTTPException(
            status_code=400, detail=f"{in_use} user(s) still hold this role"
        )
    audit.log(
        db,
        actor,
        "role.delete",
        entity_type="role",
        entity_id=role.id,
        summary=f"Deleted role '{role.name}'",
        ip=client_ip(request),
    )
    db.delete(role)
    db.commit()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    action: str = "",
    entity_type: str = "",
    actor_email: str = "",
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    actor: User = Depends(require_perm(AUDIT_READ)),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_email:
        query = query.filter(AuditLog.actor_email.ilike(f"%{actor_email}%"))
    rows = (
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    )
    return [AuditLogOut.model_validate(r) for r in rows]
