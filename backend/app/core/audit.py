"""Audit-log helper.

Every mutation performed through the admin surface records who did what,
to which entity, and when.
"""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import AuditLog, User


def log(
    db: Session,
    actor: User | None,
    action: str,
    *,
    entity_type: str = "",
    entity_id: Any = "",
    summary: str = "",
    detail: dict | None = None,
    ip: str = "",
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else "",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id != "" else "",
        summary=summary[:400],
        detail_json=json.dumps(detail, default=str) if detail else "",
        ip_address=ip,
    )
    db.add(entry)
    return entry


def diff(before: dict, after: dict) -> dict:
    """Field-level change set, for the audit detail payload."""
    changes: dict[str, dict] = {}
    for key, new_value in after.items():
        old_value = before.get(key)
        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}
    return changes
