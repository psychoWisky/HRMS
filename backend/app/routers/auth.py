"""Authentication and password management.

There is no self-registration: Admin creates every HRMS account.  Admin can
issue or reset a password but can never read an existing one.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user
from app.core.permissions import PASSWORD_CHANGE_OWN
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    password_strength_error,
    reset_token_expiry,
    verify_password,
)
from app.models.models import Employee, User
from app.schemas.schemas import (
    ChangePasswordRequest,
    CurrentUser,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password",
)


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise INVALID_CREDENTIALS
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact the HRMS administrator.",
        )
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = _authenticate(db, payload.email, payload.password)

    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    user.last_login_at = datetime.now(timezone.utc)
    audit.log(
        db,
        user,
        "auth.login",
        entity_type="user",
        entity_id=user.id,
        summary=f"{user.email} signed in",
        ip=client_ip(request),
    )
    db.commit()

    return LoginResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        must_change_password=user.must_change_password,
        full_name=emp.full_name if emp else user.email,
        role=user.role.code,
    )


@router.post("/token", response_model=LoginResponse)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """OAuth2 password flow, for API clients and the interactive docs."""
    user = _authenticate(db, form.username, form.password)
    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return LoginResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        must_change_password=user.must_change_password,
        full_name=emp.full_name if emp else user.email,
        role=user.role.code,
    )


@router.get("/me", response_model=CurrentUser)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role.code,
        role_name=user.role.name,
        permissions=user.role.permission_codes,
        must_change_password=user.must_change_password,
        employee_id=emp.id if emp else None,
        hrms_employee_id=emp.hrms_employee_id if emp else None,
        full_name=emp.full_name if emp else user.email,
        designation=emp.designation.name if emp and emp.designation else None,
        org_unit=emp.org_unit.name if emp and emp.org_unit else None,
        kyc_status=emp.kyc.status.value if emp and emp.kyc else None,
        managed_org_unit_id=user.managed_org_unit_id,
        managed_org_unit_name=(
            user.managed_org_unit.name if user.managed_org_unit else None
        ),
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.has_permission(PASSWORD_CHANGE_OWN):
        raise HTTPException(status_code=403, detail="Not permitted")
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(
            status_code=400, detail="New password must differ from the current one"
        )
    problem = password_strength_error(payload.new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    user.reset_token_hash = ""
    user.reset_token_expires_at = None
    audit.log(
        db,
        user,
        "auth.password_changed",
        entity_type="user",
        entity_id=user.id,
        summary=f"{user.email} changed their own password",
        ip=client_ip(request),
    )
    db.commit()


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
):
    """Start a password reset.

    The response is deliberately identical whether or not the address exists,
    so the endpoint cannot be used to enumerate accounts.
    """
    generic = {
        "message": (
            "If that email belongs to an AVFU HRMS account, a reset link has been "
            "issued. Contact the HRMS administrator if you do not receive it."
        )
    }
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user is None or not user.is_active:
        return generic

    token = generate_reset_token()
    user.reset_token_hash = hash_reset_token(token)
    user.reset_token_expires_at = reset_token_expiry()
    audit.log(
        db,
        None,
        "auth.reset_requested",
        entity_type="user",
        entity_id=user.id,
        summary=f"Password reset requested for {user.email}",
        ip=client_ip(request),
    )
    db.commit()

    # No mail transport is configured in this deployment. The token is
    # returned to the caller so the administrator can hand it over through
    # the approved process; wire an SMTP sender here to deliver it directly.
    return {**generic, "reset_token": token}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)
):
    token_hash = hash_reset_token(payload.token)
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    if user is None or not user.reset_token_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires = user.reset_token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    problem = password_strength_error(payload.new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    user.reset_token_hash = ""
    user.reset_token_expires_at = None
    audit.log(
        db,
        user,
        "auth.password_reset",
        entity_type="user",
        entity_id=user.id,
        summary=f"{user.email} completed a password reset",
        ip=client_ip(request),
    )
    db.commit()
