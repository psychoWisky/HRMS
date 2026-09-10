"""Authentication and permission dependencies.

Every permission is enforced here, on the backend, regardless of what the
frontend chooses to render.
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import Employee, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise CRED_EXC
    payload = decode_token(token)
    if payload is None:
        raise CRED_EXC
    user_id = payload.get("sub")
    if user_id is None:
        raise CRED_EXC
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise CRED_EXC
    if user.role is None or not user.role.is_active:
        raise HTTPException(status_code=403, detail="Your role is not active")
    return user


def get_current_employee(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Employee:
    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    if emp is None:
        raise HTTPException(
            status_code=404,
            detail="No employee record is linked to this login. Contact the HRMS administrator.",
        )
    return emp


def require_perm(*codes: str):
    """Require every listed permission code."""

    def checker(user: User = Depends(get_current_user)) -> User:
        missing = [c for c in codes if not user.has_permission(c)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission for this action ({', '.join(missing)})",
            )
        return user

    return checker


def require_any_perm(*codes: str):
    """Require at least one of the listed permission codes."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_permission(c) for c in codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission for this action",
            )
        return user

    return checker


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""
