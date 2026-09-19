"""Designations, sanctioned posts and vacancy tracking."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import audit
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user, require_perm
from app.core.permissions import DESIGNATION_MANAGE, ORG_READ, POST_MANAGE
from app.models.models import Designation, Employee, OrgUnit, Post, User
from app.schemas.schemas import (
    DesignationCreate,
    DesignationOut,
    DesignationUpdate,
    PostCreate,
    PostOut,
    PostUpdate,
)
from app.services.hierarchy import occupied_counts
from app.services.org import (
    assert_unit_in_scope,
    department_scope_ids,
    org_unit_descendant_ids as org_descendant_ids,
)
from app.services.serializers import post_out

router = APIRouter(prefix="/api", tags=["Designations & Posts"])


# ---------------------------------------------------------------------------
# Designations
# ---------------------------------------------------------------------------
@router.get("/designations", response_model=list[DesignationOut])
def list_designations(
    q: str = "",
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.has_permission(ORG_READ):
        raise HTTPException(status_code=403, detail="Not permitted")

    query = db.query(Designation)
    if q:
        query = query.filter(Designation.name.ilike(f"%{q.strip()}%"))
    if not include_inactive:
        query = query.filter(Designation.is_active.is_(True))
    designations = query.order_by(Designation.rank_level, Designation.name).all()

    sanctioned_rows = (
        db.query(Post.designation_id, func.sum(Post.sanctioned_count))
        .filter(Post.is_active.is_(True))
        .group_by(Post.designation_id)
        .all()
    )
    sanctioned = {d_id: int(total or 0) for d_id, total in sanctioned_rows}

    employee_rows = (
        db.query(Employee.designation_id, func.count(Employee.id))
        .filter(Employee.is_active.is_(True), Employee.designation_id.isnot(None))
        .group_by(Employee.designation_id)
        .all()
    )
    employed = {d_id: count for d_id, count in employee_rows}

    out: list[DesignationOut] = []
    for d in designations:
        total_sanctioned = sanctioned.get(d.id, 0)
        occupied = employed.get(d.id, 0)
        out.append(
            DesignationOut(
                id=d.id,
                name=d.name,
                short_name=d.short_name,
                category=d.category,
                rank_level=d.rank_level,
                description=d.description,
                is_active=d.is_active,
                sanctioned_total=total_sanctioned,
                occupied_total=occupied,
                vacant_total=max(total_sanctioned - occupied, 0),
                employee_count=occupied,
            )
        )
    return out


@router.post(
    "/designations", response_model=DesignationOut, status_code=status.HTTP_201_CREATED
)
def create_designation(
    payload: DesignationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(DESIGNATION_MANAGE)),
):
    exists = (
        db.query(Designation)
        .filter(func.lower(Designation.name) == payload.name.strip().lower())
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="That designation already exists")
    d = Designation(**payload.model_dump())
    d.name = d.name.strip()
    db.add(d)
    db.flush()
    audit.log(
        db,
        user,
        "designation.create",
        entity_type="designation",
        entity_id=d.id,
        summary=f"Created designation '{d.name}'",
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(d)
    return DesignationOut.model_validate(d)


@router.put("/designations/{designation_id}", response_model=DesignationOut)
def update_designation(
    designation_id: int,
    payload: DesignationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(DESIGNATION_MANAGE)),
):
    d = db.get(Designation, designation_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Designation not found")
    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(d, k) for k in changes}
    for key, value in changes.items():
        setattr(d, key, value)
    audit.log(
        db,
        user,
        "designation.update",
        entity_type="designation",
        entity_id=d.id,
        summary=f"Updated designation '{d.name}'",
        detail=audit.diff(before, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(d)
    return DesignationOut.model_validate(d)


@router.delete(
    "/designations/{designation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def deactivate_designation(
    designation_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(DESIGNATION_MANAGE)),
):
    d = db.get(Designation, designation_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Designation not found")
    d.is_active = False
    audit.log(
        db,
        user,
        "designation.deactivate",
        entity_type="designation",
        entity_id=d.id,
        summary=f"Deactivated designation '{d.name}'",
        ip=client_ip(request),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Sanctioned posts
# ---------------------------------------------------------------------------
@router.get("/posts", response_model=list[PostOut])
def list_posts(
    org_unit_id: int | None = None,
    designation_id: int | None = None,
    include_subtree: bool = True,
    vacant_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.has_permission(ORG_READ):
        raise HTTPException(status_code=403, detail="Not permitted")

    query = db.query(Post).filter(Post.is_active.is_(True))
    if org_unit_id is not None:
        if include_subtree:
            query = query.filter(
                Post.org_unit_id.in_(org_descendant_ids(db, org_unit_id))
            )
        else:
            query = query.filter(Post.org_unit_id == org_unit_id)
    if designation_id is not None:
        query = query.filter(Post.designation_id == designation_id)

    scope = department_scope_ids(db, user)
    if scope is not None:
        query = query.filter(Post.org_unit_id.in_(scope))

    occupied = occupied_counts(db)
    # `posts` has two FKs to `designations`, so the join must be explicit.
    posts = (
        query.join(Designation, Post.designation_id == Designation.id)
        .order_by(Designation.rank_level, Designation.name)
        .all()
    )

    result = [post_out(p, occupied.get(p.id, 0)) for p in posts]
    if vacant_only:
        result = [p for p in result if p.vacant_count > 0]
    return result


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(POST_MANAGE)),
):
    if db.get(OrgUnit, payload.org_unit_id) is None:
        raise HTTPException(status_code=400, detail="Org unit not found")
    assert_unit_in_scope(db, user, payload.org_unit_id)
    if db.get(Designation, payload.designation_id) is None:
        raise HTTPException(status_code=400, detail="Designation not found")
    duplicate = (
        db.query(Post)
        .filter(
            Post.org_unit_id == payload.org_unit_id,
            Post.designation_id == payload.designation_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="That designation already has a sanctioned post in this office",
        )
    post = Post(**payload.model_dump())
    db.add(post)
    db.flush()
    audit.log(
        db,
        user,
        "post.create",
        entity_type="post",
        entity_id=post.id,
        summary=(
            f"Sanctioned {post.sanctioned_count} post(s) of "
            f"{post.designation.name} in {post.org_unit.name}"
        ),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(post)
    return post_out(post, occupied_counts(db).get(post.id, 0))


@router.put("/posts/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    payload: PostUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(POST_MANAGE)),
):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    assert_unit_in_scope(db, user, post.org_unit_id)

    changes = payload.model_dump(exclude_unset=True)
    new_sanctioned = changes.get("sanctioned_count", post.sanctioned_count)
    occupied = occupied_counts(db).get(post.id, 0)
    if new_sanctioned < occupied:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{occupied} employee(s) already hold this post; the sanctioned "
                f"strength cannot be lowered below that"
            ),
        )

    before = {k: getattr(post, k) for k in changes}
    for key, value in changes.items():
        setattr(post, key, value)
    audit.log(
        db,
        user,
        "post.update",
        entity_type="post",
        entity_id=post.id,
        summary=f"Updated sanctioned post #{post.id}",
        detail=audit.diff(before, changes),
        ip=client_ip(request),
    )
    db.commit()
    db.refresh(post)
    return post_out(post, occupied_counts(db).get(post.id, 0))


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm(POST_MANAGE)),
):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    assert_unit_in_scope(db, user, post.org_unit_id)
    held = db.query(Employee).filter(Employee.post_id == post_id).count()
    if held:
        raise HTTPException(
            status_code=400,
            detail=f"{held} employee(s) are assigned to this post",
        )
    audit.log(
        db,
        user,
        "post.delete",
        entity_type="post",
        entity_id=post_id,
        summary=f"Deleted sanctioned post #{post_id}",
        ip=client_ip(request),
    )
    db.delete(post)
    db.commit()
