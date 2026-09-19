"""Storage for uploaded documents.

Files live outside the web root and are only ever served through endpoints
that check authorisation first — nothing here is publicly addressable.
"""
from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

DOCUMENT_TYPES = [
    "Aadhaar Card",
    "PAN Card",
    "Appointment Letter",
    "Educational Certificate",
    "Experience Certificate",
    "Bank Passbook",
    "Photograph",
    "Date of Birth Proof",
    "Date of Joining AAU/AVFU Proof",
    "Date of Joining Present Post Proof",
    "Retirement Date Calculation Proof",
    "Other",
]


def _folder(scope: str, owner_id: int) -> Path:
    path = settings.upload_path / scope / str(owner_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(scope: str, owner_id: int, file: UploadFile) -> tuple[str, bytes]:
    """Validate and persist an upload. Returns (stored_filename, contents)."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPEG, PNG or WebP files are accepted",
        )

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit",
        )

    suffix = Path(file.filename or "").suffix[:10]
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    (_folder(scope, owner_id) / stored_name).write_bytes(contents)
    return stored_name, contents


def file_path(scope: str, owner_id: int, stored_filename: str) -> Path:
    return settings.upload_path / scope / str(owner_id) / stored_filename


def send_file(
    scope: str, owner_id: int, stored_filename: str, content_type: str, filename: str
) -> FileResponse:
    path = file_path(scope, owner_id, stored_filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(
        path,
        media_type=content_type or "application/octet-stream",
        filename=filename,
    )


def delete_file(scope: str, owner_id: int, stored_filename: str) -> None:
    file_path(scope, owner_id, stored_filename).unlink(missing_ok=True)


def move_file(
    from_scope: str, from_id: int, to_scope: str, to_id: int, stored_filename: str
) -> None:
    """Relocate a stored file when a submission is admitted into the HRMS."""
    source = file_path(from_scope, from_id, stored_filename)
    if not source.exists():
        return
    target = _folder(to_scope, to_id) / stored_filename
    source.replace(target)
