"""HR/Admin-configurable employee fields and document requirements.

Neither requires a code change to add: HR/Admin defines a field (or an
extra required document type) here, optionally scoped to one department,
and it immediately shows up wherever employee data is collected — the
Employee profile form and the new-employee submission form.

Department Head can use/view fields that apply to their department but
cannot create or modify definitions (enforced by ``CUSTOM_FIELD_MANAGE``
being granted only to Admin/HR).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user, require_perm
from app.core.permissions import CUSTOM_FIELD_MANAGE
from app.models.models import (
    CustomDocumentRequirement,
    CustomFieldDefinition,
    CustomFieldValue,
    Employee,
    OrgUnit,
)
from app.schemas.schemas import (
    CustomDocumentRequirementCreate,
    CustomDocumentRequirementOut,
    CustomDocumentRequirementUpdate,
    CustomFieldCreate,
    CustomFieldOut,
    CustomFieldUpdate,
    CustomFieldValueIn,
    CustomFieldValueOut,
)
from app.services.org import assert_employee_in_scope, org_unit_ancestors

router = APIRouter(prefix="/api/custom-fields", tags=["Custom Fields"])
doc_router = APIRouter(prefix="/api/custom-documents", tags=["Custom Fields"])


def _field_out(f: CustomFieldDefinition) -> CustomFieldOut:
    return CustomFieldOut(
        id=f.id,
        key=f.key,
        label=f.label,
        field_type=f.field_type,
        options=f.options,
        is_required=f.is_required,
        org_unit_id=f.org_unit_id,
        org_unit_name=f.org_unit.name if f.org_unit else None,
        help_text=f.help_text,
        sort_order=f.sort_order,
        is_active=f.is_active,
    )


def _doc_out(d: CustomDocumentRequirement) -> CustomDocumentRequirementOut:
    return CustomDocumentRequirementOut(
        id=d.id,
        label=d.label,
        org_unit_id=d.org_unit_id,
        org_unit_name=d.org_unit.name if d.org_unit else None,
        is_required=d.is_required,
        is_active=d.is_active,
    )


def applicable_fields(
    db: Session, org_unit_id: int | None, *, active_only: bool = True
) -> list[CustomFieldDefinition]:
    """University-wide fields plus those scoped to this unit or an ancestor."""
    scope_ids: set[int | None] = {None}
    if org_unit_id is not None:
        scope_ids.add(org_unit_id)
        scope_ids.update(a.id for a in org_unit_ancestors(db, org_unit_id))
    query = db.query(CustomFieldDefinition).filter(
        CustomFieldDefinition.org_unit_id.in_(scope_ids)
    )
    if active_only:
        query = query.filter(CustomFieldDefinition.is_active.is_(True))
    return query.order_by(CustomFieldDefinition.sort_order, CustomFieldDefinition.label).all()


def applicable_document_labels(db: Session, org_unit_id: int | None) -> list[str]:
    scope_ids: set[int | None] = {None}
    if org_unit_id is not None:
        scope_ids.add(org_unit_id)
        scope_ids.update(a.id for a in org_unit_ancestors(db, org_unit_id))
    rows = (
        db.query(CustomDocumentRequirement)
        .filter(
            CustomDocumentRequirement.org_unit_id.in_(scope_ids),
            CustomDocumentRequirement.is_active.is_(True),
        )
        .order_by(CustomDocumentRequirement.label)
        .all()
    )
    return [r.label for r in rows]


# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------
@router.get("", response_model=list[CustomFieldOut])
def list_fields(
    db: Session = Depends(get_db), user=Depends(get_current_user)
):
    # Read is open to any authenticated administrative user (incl.
    # Department Head, who may use but not edit these fields).
    rows = (
        db.query(CustomFieldDefinition)
        .order_by(CustomFieldDefinition.sort_order, CustomFieldDefinition.label)
        .all()
    )
    return [_field_out(f) for f in rows]


@router.post("", response_model=CustomFieldOut, status_code=status.HTTP_201_CREATED)
def create_field(
    payload: CustomFieldCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_perm(CUSTOM_FIELD_MANAGE)),
):
    if db.query(CustomFieldDefinition).filter(
        CustomFieldDefinition.key == payload.key
    ).first():
        raise HTTPException(status_code=409, detail="That field key already exists")
    if payload.org_unit_id is not None and db.get(
        OrgUnit, payload.org_unit_id
    ) is None:
        raise HTTPException(status_code=400, detail="Organisation not found")

    field = CustomFieldDefinition(
        key=payload.key.strip(),
        label=payload.label.strip(),
        field_type=payload.field_type,
        options_csv=",".join(payload.options),
        is_required=payload.is_required,
        org_unit_id=payload.org_unit_id,
        help_text=payload.help_text,
        sort_order=payload.sort_order,
        created_by_id=user.id,
    )
    db.add(field)
    db.flush()
    audit.log(
        db,
        user,
        "custom_field.create",
        entity_type="custom_field",
        entity_id=field.id,
        summary=f"Created custom field '{field.label}'",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(field)
    return _field_out(field)


@router.put("/{field_id}", response_model=CustomFieldOut)
def update_field(
    field_id: int,
    payload: CustomFieldUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_perm(CUSTOM_FIELD_MANAGE)),
):
    field = db.get(CustomFieldDefinition, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Custom field not found")
    changes = payload.model_dump(exclude_unset=True)
    options = changes.pop("options", None)
    for key, value in changes.items():
        setattr(field, key, value)
    if options is not None:
        field.options_csv = ",".join(options)
    audit.log(
        db,
        user,
        "custom_field.update",
        entity_type="custom_field",
        entity_id=field.id,
        summary=f"Updated custom field '{field.label}'",
        detail=audit.diff({}, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(field)
    return _field_out(field)


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_field(
    field_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_perm(CUSTOM_FIELD_MANAGE)),
):
    field = db.get(CustomFieldDefinition, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Custom field not found")
    field.is_active = False
    audit.log(
        db,
        user,
        "custom_field.deactivate",
        entity_type="custom_field",
        entity_id=field.id,
        summary=f"Deactivated custom field '{field.label}'",
        ip=client_ip(request),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Values on one employee
# ---------------------------------------------------------------------------
@router.get("/employee/{employee_id}", response_model=list[CustomFieldValueOut])
def get_employee_field_values(
    employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    assert_employee_in_scope(db, user, emp)

    fields = applicable_fields(db, emp.org_unit_id)
    values = {
        v.field_id: v.value
        for v in db.query(CustomFieldValue).filter(
            CustomFieldValue.employee_id == employee_id
        )
    }
    return [
        CustomFieldValueOut(
            field_id=f.id,
            key=f.key,
            label=f.label,
            field_type=f.field_type,
            value=values.get(f.id, ""),
        )
        for f in fields
    ]


@router.put("/employee/{employee_id}", response_model=list[CustomFieldValueOut])
def set_employee_field_values(
    employee_id: int,
    payload: list[CustomFieldValueIn],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """HR/Admin/Department Head fill in custom field values for an employee.

    Any authenticated administrative user with employee-edit rights over
    this employee may set values; only Admin/HR may define the fields
    themselves (see ``create_field`` / ``update_field`` above).
    """
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    assert_employee_in_scope(db, user, emp)

    valid_ids = {f.id for f in applicable_fields(db, emp.org_unit_id, active_only=False)}
    for item in payload:
        if item.field_id not in valid_ids:
            raise HTTPException(
                status_code=400, detail=f"Field {item.field_id} does not apply here"
            )
        existing = (
            db.query(CustomFieldValue)
            .filter(
                CustomFieldValue.field_id == item.field_id,
                CustomFieldValue.employee_id == employee_id,
            )
            .first()
        )
        if existing:
            existing.value = item.value
        else:
            db.add(
                CustomFieldValue(
                    field_id=item.field_id, employee_id=employee_id, value=item.value
                )
            )
    db.commit()
    return get_employee_field_values(employee_id, db=db, user=user)


# ---------------------------------------------------------------------------
# Custom document requirements
# ---------------------------------------------------------------------------
@doc_router.get("", response_model=list[CustomDocumentRequirementOut])
def list_document_requirements(
    db: Session = Depends(get_db), user=Depends(get_current_user)
):
    rows = (
        db.query(CustomDocumentRequirement)
        .order_by(CustomDocumentRequirement.label)
        .all()
    )
    return [_doc_out(d) for d in rows]


@doc_router.post(
    "", response_model=CustomDocumentRequirementOut, status_code=status.HTTP_201_CREATED
)
def create_document_requirement(
    payload: CustomDocumentRequirementCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_perm(CUSTOM_FIELD_MANAGE)),
):
    if db.query(CustomDocumentRequirement).filter(
        CustomDocumentRequirement.label == payload.label
    ).first():
        raise HTTPException(status_code=409, detail="That document type already exists")
    if payload.org_unit_id is not None and db.get(
        OrgUnit, payload.org_unit_id
    ) is None:
        raise HTTPException(status_code=400, detail="Organisation not found")
    doc = CustomDocumentRequirement(
        label=payload.label.strip(),
        org_unit_id=payload.org_unit_id,
        is_required=payload.is_required,
        created_by_id=user.id,
    )
    db.add(doc)
    db.flush()
    audit.log(
        db,
        user,
        "custom_document.create",
        entity_type="custom_document",
        entity_id=doc.id,
        summary=f"Added required document type '{doc.label}'",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@doc_router.put("/{doc_id}", response_model=CustomDocumentRequirementOut)
def update_document_requirement(
    doc_id: int,
    payload: CustomDocumentRequirementUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_perm(CUSTOM_FIELD_MANAGE)),
):
    doc = db.get(CustomDocumentRequirement, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document requirement not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(doc, key, value)
    audit.log(
        db,
        user,
        "custom_document.update",
        entity_type="custom_document",
        entity_id=doc.id,
        summary=f"Updated document requirement '{doc.label}'",
        detail=audit.diff({}, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@doc_router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_document_requirement(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_perm(CUSTOM_FIELD_MANAGE)),
):
    doc = db.get(CustomDocumentRequirement, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document requirement not found")
    doc.is_active = False
    audit.log(
        db,
        user,
        "custom_document.deactivate",
        entity_type="custom_document",
        entity_id=doc.id,
        summary=f"Deactivated document requirement '{doc.label}'",
        ip=client_ip(request),
    )
    db.commit()
