"""Password hashing, JWT issuance and password-reset token handling.

Plaintext passwords are never stored, logged or returned.  Reset tokens are
issued once and only their SHA-256 hash is persisted.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import string

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt operates on bytes and silently truncates beyond 72 bytes.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8")[:_BCRYPT_MAX_BYTES], hashed.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# --- temporary credentials & reset tokens -----------------------------------
_TEMP_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits


def generate_temporary_password(length: int = 12) -> str:
    """A readable one-time password for Admin to hand to the employee."""
    return "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(length))


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )


def password_strength_error(password: str) -> str | None:
    """Return a human-readable problem, or None when the password is fine."""
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return (
            f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long"
        )
    if not any(c.isalpha() for c in password):
        return "Password must contain at least one letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit"
    return None
