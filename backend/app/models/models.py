"""AVFU HRMS — data model.

One centralised HRMS for the whole university.  Campus/location is
organisational data, never a separate authentication boundary.

The organisational hierarchy is a single fixed-depth tree of ``OrgUnit``
rows discriminated by ``kind``:

    College  ->  Establishment | Department  ->  Section/Unit/Cell

A College is a top-level node (``parent_id is None``).  A Department may
sit directly under a College or under an Establishment.  Every Employee is
attached to exactly one ``OrgUnit`` (at any level) plus a Designation and,
optionally, a sanctioned Post.
"""
from datetime import date, datetime, timezone
import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Enumerations
# ============================================================================
class OrgUnitKind(str, enum.Enum):
    """The level of a node in the fixed AVFU hierarchy.

        college       -> a constituent College (AVFU root, CVSc, CFSc, LCVSc).
                         Top level; ``parent_id is None``.
        establishment -> an administrative office (Directorate, Office,
                         Research Station). Parent is a College.
        department    -> an academic teaching department. Parent is a College
                         or an Establishment.
        section       -> a Section / Unit / Cell under an office (Part C of the
                         AVFU submission format). Parent is an Establishment or
                         a Department. ``sub_kind`` says which of the three.
    """

    college = "college"
    establishment = "establishment"
    department = "department"
    section = "section"


class DesignationCategory(str, enum.Enum):
    officer = "officer"
    teaching = "teaching"
    scientific = "scientific"
    administrative = "administrative"
    accounts = "accounts"
    technical = "technical"
    support = "support"


class EmploymentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    retired = "retired"
    transferred = "transferred"


class KYCStatus(str, enum.Enum):
    not_started = "not_started"
    draft = "draft"
    submitted = "submitted"
    under_verification = "under_verification"
    verified = "verified"
    rejected = "rejected"
    resubmission_required = "resubmission_required"


class ReportingType(str, enum.Enum):
    administrative = "administrative"
    functional = "functional"


class SubmissionStatus(str, enum.Enum):
    """Lifecycle of a new-employee document submission.

    The applicant creates the submission themselves from the public joining
    link and moves it to ``submitted`` once complete.
    """

    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    resubmission_required = "resubmission_required"
    approved = "approved"
    rejected = "rejected"


class CustomFieldType(str, enum.Enum):
    text = "text"
    number = "number"
    date = "date"
    boolean = "boolean"
    select = "select"


class PositionEventType(str, enum.Enum):
    """One entry in an employee's history/timeline."""

    joining = "joining"
    promotion = "promotion"
    establishment_change = "establishment_change"
    employee_id_change = "employee_id_change"
    other = "other"


# ============================================================================
# RBAC — Role / Permission
# ============================================================================
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Permission(Base):
    """A single capability, e.g. ``employee:create``."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    group: Mapped[str] = mapped_column(String(40), default="")
    description: Mapped[str] = mapped_column(String(200), default="")

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200), default="")
    # System roles cannot be deleted, but their permissions stay configurable.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    # Hidden from the Roles & Users management screen. Used for the Super
    # Admin technical role, which must never appear as an assignable
    # "normal" role — it still exists and works if assigned directly.
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    users: Mapped[list["User"]] = relationship(back_populates="role")

    @property
    def permission_codes(self) -> list[str]:
        return sorted(p.code for p in self.permissions)


# ============================================================================
# Identity
# ============================================================================
class User(Base):
    """Login identity.  Passwords are only ever stored as bcrypt hashes."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Forces the change-password screen on next sign-in (initial/temporary
    # credentials issued by Admin).
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Password-reset: only a hash of the token is stored, never the token.
    reset_token_hash: Mapped[str] = mapped_column(String(255), default="")
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Set only for Department Head accounts: the one org unit (and
    # everything beneath it) they are permitted to manage. Null for
    # Admin/HR/Super Admin, whose access is university-wide.
    managed_org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id", use_alter=True, name="fk_user_managed_unit"),
        nullable=True,
    )

    role: Mapped[Role] = relationship(back_populates="users", lazy="selectin")
    managed_org_unit: Mapped["OrgUnit"] = relationship(
        foreign_keys=[managed_org_unit_id], lazy="selectin"
    )
    employee: Mapped["Employee"] = relationship(
        back_populates="user",
        uselist=False,
        foreign_keys="Employee.user_id",
    )

    def has_permission(self, code: str) -> bool:
        if not self.is_active or self.role is None or not self.role.is_active:
            return False
        return any(p.code == code for p in self.role.permissions)


# ============================================================================
# Places & organisation tree
# ============================================================================
class Location(Base):
    """A physical campus / office location.

    Kept separate from the org tree because one campus (e.g. Khanapara)
    hosts several unrelated organisational branches.
    """

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    district: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(80), default="Assam")
    pincode: Mapped[str] = mapped_column(String(12), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    org_units: Mapped[list["OrgUnit"]] = relationship(back_populates="location")


class OrgUnit(Base):
    """One node of the fixed AVFU hierarchy — see the module docstring.

    ``kind`` places the node on the College -> Establishment|Department ->
    Section ladder. The Part A "General Information" of the AVFU submission
    format lives on the ``establishment``/``department`` rows; the Part C
    "Sections/Units/Cells" list is the ``section`` children of an office.
    """

    __tablename__ = "org_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[OrgUnitKind] = mapped_column(
        Enum(OrgUnitKind), default=OrgUnitKind.section, index=True
    )
    # Only meaningful for kind == section: "section" | "unit" | "cell".
    sub_kind: Mapped[str] = mapped_column(String(12), default="")

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    # The ID segment: AVFU / <establishment short_code> / <department short_code|GEN> / serial.
    # Required (uppercase) for college and establishment; used for department too.
    short_code: Mapped[str] = mapped_column(String(20), default="", index=True)
    code: Mapped[str] = mapped_column(String(40), default="", index=True)

    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # --- Part A: General Information (establishment / department) ---
    head_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", use_alter=True, name="fk_orgunit_head"),
        nullable=True,
    )
    reporting_authority_text: Mapped[str] = mapped_column(String(300), default="")
    hrms_contact_name: Mapped[str] = mapped_column(String(160), default="")
    hrms_contact_designation: Mapped[str] = mapped_column(String(160), default="")
    hrms_contact_phone: Mapped[str] = mapped_column(String(40), default="")
    hrms_contact_email: Mapped[str] = mapped_column(String(160), default="")
    office_email: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    # --- Part C: Sections/Units/Cells (section only) ---
    officer_in_charge_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", use_alter=True, name="fk_orgunit_oic"),
        nullable=True,
    )
    headcount_note: Mapped[str] = mapped_column(String(60), default="")

    parent: Mapped["OrgUnit"] = relationship(
        remote_side="OrgUnit.id",
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children: Mapped[list["OrgUnit"]] = relationship(
        foreign_keys=[parent_id],
        back_populates="parent",
        order_by="OrgUnit.sort_order, OrgUnit.name",
    )
    location: Mapped[Location | None] = relationship(
        back_populates="org_units", lazy="selectin"
    )
    head: Mapped["Employee"] = relationship(
        foreign_keys=[head_employee_id], post_update=True
    )
    officer_in_charge: Mapped["Employee"] = relationship(
        foreign_keys=[officer_in_charge_employee_id], post_update=True
    )
    posts: Mapped[list["Post"]] = relationship(
        back_populates="org_unit", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="org_unit", foreign_keys="Employee.org_unit_id"
    )


# ============================================================================
# Designations & sanctioned posts
# ============================================================================
class Designation(Base):
    __tablename__ = "designations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    short_name: Mapped[str] = mapped_column(String(40), default="")
    category: Mapped[DesignationCategory] = mapped_column(
        Enum(DesignationCategory), default=DesignationCategory.administrative
    )
    # Lower rank_level = more senior.  Drives org-chart ordering.
    rank_level: Mapped[int] = mapped_column(Integer, default=50)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    posts: Mapped[list["Post"]] = relationship(
        back_populates="designation", foreign_keys="Post.designation_id"
    )


class Post(Base):
    """A sanctioned post: N seats of one designation inside one office."""

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("org_unit_id", "designation_id", name="uq_post_unit_desig"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_unit_id: Mapped[int] = mapped_column(
        ForeignKey("org_units.id"), index=True
    )
    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.id"), index=True
    )

    # Part B "Level" column — used only to order the rows on the office page.
    level_no: Mapped[int] = mapped_column(Integer, default=0)

    sanctioned_count: Mapped[int] = mapped_column(Integer, default=0)
    # Vacancy as stated in the client document, kept for reference alongside
    # the value computed from actual employee assignments.
    reported_vacant_count: Mapped[int] = mapped_column(Integer, default=0)

    level_label: Mapped[str] = mapped_column(String(20), default="")
    # Part B "To Report" free text from the source documents, e.g. "HOD/Dean/Registrar".
    reports_to_note: Mapped[str] = mapped_column(String(255), default="")
    reports_to_designation_id: Mapped[int | None] = mapped_column(
        ForeignKey("designations.id"), nullable=True
    )
    remarks: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    org_unit: Mapped[OrgUnit] = relationship(back_populates="posts")
    designation: Mapped[Designation] = relationship(
        back_populates="posts", foreign_keys=[designation_id], lazy="selectin"
    )
    reports_to_designation: Mapped[Designation] = relationship(
        foreign_keys=[reports_to_designation_id]
    )
    employees: Mapped[list["Employee"]] = relationship(back_populates="post")


# ============================================================================
# Employee
# ============================================================================
class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=True
    )

    # The permanent AVFU HRMS identity.
    hrms_employee_id: Mapped[str] = mapped_column(
        String(30), unique=True, index=True
    )

    full_name: Mapped[str] = mapped_column(String(160), index=True)
    gender: Mapped[str] = mapped_column(String(20), default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    official_email: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    photo_url: Mapped[str] = mapped_column(String(255), default="")

    # The one node this employee is attached to (any level of the tree).
    org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True, index=True
    )
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True
    )
    designation_id: Mapped[int | None] = mapped_column(
        ForeignKey("designations.id"), nullable=True
    )
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    pay_scale: Mapped[str] = mapped_column(String(80), default="")

    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(EmploymentStatus), default=EmploymentStatus.active
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)
    remarks: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(
        back_populates="employee", foreign_keys=[user_id], lazy="selectin"
    )
    org_unit: Mapped[OrgUnit | None] = relationship(
        back_populates="employees", foreign_keys=[org_unit_id], lazy="selectin"
    )
    location: Mapped[Location] = relationship(lazy="selectin")
    designation: Mapped[Designation] = relationship(lazy="selectin")
    post: Mapped[Post] = relationship(back_populates="employees", foreign_keys=[post_id])

    kyc: Mapped["KYC"] = relationship(
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="KYC.employee_id",
    )
    reporting_links: Mapped[list["ReportingRelationship"]] = relationship(
        back_populates="employee",
        foreign_keys="ReportingRelationship.employee_id",
        cascade="all, delete-orphan",
    )
    position_history: Mapped[list["PositionHistory"]] = relationship(
        back_populates="employee",
        foreign_keys="PositionHistory.employee_id",
        cascade="all, delete-orphan",
        order_by="PositionHistory.effective_date, PositionHistory.created_at",
    )
    custom_field_values: Mapped[list["CustomFieldValue"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class ReportingRelationship(Base):
    """Who reports to whom.

    A separate entity rather than a single ``reports_to_id`` column because
    the AVFU source documents genuinely record multi-valued reporting
    (e.g. "Assistant Professor -> HOD/Dean/Registrar").  Exactly one link
    per employee is ``is_primary``.
    """

    __tablename__ = "reporting_relationships"
    __table_args__ = (
        UniqueConstraint("employee_id", "reports_to_id", name="uq_report_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    reports_to_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)

    relationship_type: Mapped[ReportingType] = mapped_column(
        Enum(ReportingType), default=ReportingType.administrative
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[Employee] = relationship(
        back_populates="reporting_links", foreign_keys=[employee_id]
    )
    manager: Mapped[Employee] = relationship(foreign_keys=[reports_to_id], lazy="selectin")


# ============================================================================
# Position history / timeline (joining, promotion, establishment change)
# ============================================================================
class PositionHistory(Base):
    """One append-only event in an employee's employment timeline.

    Promotion never overwrites the employee's prior designation/post/
    establishment/employee-ID — it writes a new row here and then updates
    the live ``Employee`` columns. Nothing is ever deleted from this table.
    """

    __tablename__ = "position_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    event_type: Mapped[PositionEventType] = mapped_column(
        Enum(PositionEventType), default=PositionEventType.other
    )

    previous_designation_id: Mapped[int | None] = mapped_column(
        ForeignKey("designations.id"), nullable=True
    )
    new_designation_id: Mapped[int | None] = mapped_column(
        ForeignKey("designations.id"), nullable=True
    )
    previous_org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True
    )
    new_org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True
    )
    previous_employee_code: Mapped[str] = mapped_column(String(60), default="")
    new_employee_code: Mapped[str] = mapped_column(String(60), default="")
    previous_pay_scale: Mapped[str] = mapped_column(String(80), default="")
    new_pay_scale: Mapped[str] = mapped_column(String(80), default="")

    # "Promotion date" and "date of joining the new position" are recorded
    # as the client's requirement names them separately, even though in
    # practice HR will often set both to the same day.
    promotion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_position_joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, default=date.today)

    remarks: Mapped[str] = mapped_column(String(400), default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[Employee] = relationship(
        back_populates="position_history", foreign_keys=[employee_id]
    )
    previous_designation: Mapped[Designation] = relationship(
        foreign_keys=[previous_designation_id], lazy="selectin"
    )
    new_designation: Mapped[Designation] = relationship(
        foreign_keys=[new_designation_id], lazy="selectin"
    )
    previous_org_unit: Mapped[OrgUnit] = relationship(
        foreign_keys=[previous_org_unit_id], lazy="selectin"
    )
    new_org_unit: Mapped[OrgUnit] = relationship(
        foreign_keys=[new_org_unit_id], lazy="selectin"
    )


# ============================================================================
# Configurable employee custom fields & document requirements
# ============================================================================
class CustomFieldDefinition(Base):
    """A field HR/Admin added to the employee form without a code change.

    Optionally scoped to one org unit (typically a department) — when
    ``org_unit_id`` is set, the field applies to that unit and everyone
    beneath it; when null, it applies university-wide.
    """

    __tablename__ = "custom_field_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(160))
    field_type: Mapped[CustomFieldType] = mapped_column(
        Enum(CustomFieldType), default=CustomFieldType.text
    )
    # For field_type == select: comma-separated choices.
    options_csv: Mapped[str] = mapped_column(String(500), default="")
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True
    )
    help_text: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    org_unit: Mapped[OrgUnit] = relationship(lazy="selectin")
    values: Mapped[list["CustomFieldValue"]] = relationship(
        back_populates="field", cascade="all, delete-orphan"
    )

    @property
    def options(self) -> list[str]:
        return [o.strip() for o in self.options_csv.split(",") if o.strip()]


class CustomFieldValue(Base):
    __tablename__ = "custom_field_values"
    __table_args__ = (
        UniqueConstraint("field_id", "employee_id", name="uq_custom_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(
        ForeignKey("custom_field_definitions.id"), index=True
    )
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    field: Mapped[CustomFieldDefinition] = relationship(
        back_populates="values", lazy="selectin"
    )
    employee: Mapped[Employee] = relationship(back_populates="custom_field_values")


class CustomDocumentRequirement(Base):
    """An extra required document type HR/Admin defined, beyond the
    built-in ones (qualification certificates, PAN, Aadhaar, ...).

    Optionally scoped to one department/organisation, since required
    documents may differ by department.
    """

    __tablename__ = "custom_document_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120), unique=True)
    org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    org_unit: Mapped[OrgUnit] = relationship(lazy="selectin")


# ============================================================================
# KYC — manual verification only
# ============================================================================
class KYC(Base):
    __tablename__ = "kyc"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), unique=True, index=True
    )
    status: Mapped[KYCStatus] = mapped_column(
        Enum(KYCStatus), default=KYCStatus.not_started
    )

    # --- declared information ---
    father_name: Mapped[str] = mapped_column(String(160), default="")
    mother_name: Mapped[str] = mapped_column(String(160), default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), default="")
    blood_group: Mapped[str] = mapped_column(String(8), default="")
    marital_status: Mapped[str] = mapped_column(String(30), default="")
    nationality: Mapped[str] = mapped_column(String(60), default="Indian")
    category: Mapped[str] = mapped_column(String(30), default="")

    aadhaar_number: Mapped[str] = mapped_column(String(20), default="")
    pan_number: Mapped[str] = mapped_column(String(20), default="")

    personal_email: Mapped[str] = mapped_column(String(160), default="")
    contact_phone: Mapped[str] = mapped_column(String(30), default="")
    emergency_contact_name: Mapped[str] = mapped_column(String(160), default="")
    emergency_contact_phone: Mapped[str] = mapped_column(String(30), default="")

    permanent_address: Mapped[str] = mapped_column(Text, default="")
    present_address: Mapped[str] = mapped_column(Text, default="")

    bank_name: Mapped[str] = mapped_column(String(120), default="")
    bank_account_number: Mapped[str] = mapped_column(String(40), default="")
    bank_ifsc: Mapped[str] = mapped_column(String(20), default="")

    # --- workflow ---
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verifier_remark: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    employee: Mapped[Employee] = relationship(
        back_populates="kyc", foreign_keys=[employee_id]
    )
    verified_by: Mapped[User] = relationship(foreign_keys=[verified_by_id])
    documents: Mapped[list["KYCDocument"]] = relationship(
        back_populates="kyc", cascade="all, delete-orphan"
    )
    history: Mapped[list["KYCHistory"]] = relationship(
        back_populates="kyc",
        cascade="all, delete-orphan",
        order_by="KYCHistory.created_at.desc()",
    )


class KYCDocument(Base):
    __tablename__ = "kyc_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    kyc_id: Mapped[int] = mapped_column(ForeignKey("kyc.id"), index=True)

    doc_type: Mapped[str] = mapped_column(String(60))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verifier_remark: Mapped[str] = mapped_column(String(255), default="")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    kyc: Mapped[KYC] = relationship(back_populates="documents")


class KYCHistory(Base):
    """Immutable audit trail of every KYC state change."""

    __tablename__ = "kyc_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    kyc_id: Mapped[int] = mapped_column(ForeignKey("kyc.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    from_status: Mapped[str] = mapped_column(String(30), default="")
    to_status: Mapped[str] = mapped_column(String(30), default="")
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    actor_name: Mapped[str] = mapped_column(String(160), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    kyc: Mapped[KYC] = relationship(back_populates="history")


# ============================================================================
# Public new-employee submissions (no login required)
# ============================================================================
class EmployeeSubmission(Base):
    """A new employee's own details and documents.

    This is a staging record: it is deliberately NOT an ``Employee``. The
    applicant creates it themselves from the public joining link that
    Admin/HR share. Nothing here reaches the directory until HR reviews it
    and admits the person into the HRMS.
    """

    __tablename__ = "employee_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Human-readable, shown to HR and to the applicant to track their
    # submission. This is the only handle the applicant needs.
    reference_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)

    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.draft, index=True
    )

    # --- identity ---
    full_name: Mapped[str] = mapped_column(String(160), default="", index=True)
    email: Mapped[str] = mapped_column(String(160), default="", index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    gender: Mapped[str] = mapped_column(String(20), default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- proposed placement (chosen by the applicant, confirmed by HR) ---
    org_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("org_units.id"), nullable=True
    )
    designation_id: Mapped[int | None] = mapped_column(
        ForeignKey("designations.id"), nullable=True
    )
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True
    )
    date_of_joining: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- declared KYC information ---
    father_name: Mapped[str] = mapped_column(String(160), default="")
    mother_name: Mapped[str] = mapped_column(String(160), default="")
    blood_group: Mapped[str] = mapped_column(String(8), default="")
    marital_status: Mapped[str] = mapped_column(String(30), default="")
    nationality: Mapped[str] = mapped_column(String(60), default="Indian")
    category: Mapped[str] = mapped_column(String(30), default="")
    aadhaar_number: Mapped[str] = mapped_column(String(20), default="")
    pan_number: Mapped[str] = mapped_column(String(20), default="")
    emergency_contact_name: Mapped[str] = mapped_column(String(160), default="")
    emergency_contact_phone: Mapped[str] = mapped_column(String(30), default="")
    permanent_address: Mapped[str] = mapped_column(Text, default="")
    present_address: Mapped[str] = mapped_column(Text, default="")
    bank_name: Mapped[str] = mapped_column(String(120), default="")
    bank_account_number: Mapped[str] = mapped_column(String(40), default="")
    bank_ifsc: Mapped[str] = mapped_column(String(20), default="")

    # --- workflow ---
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewer_remark: Mapped[str] = mapped_column(Text, default="")
    # Set once HR admits the applicant into the HRMS.
    created_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )

    submitter_ip: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    org_unit: Mapped[OrgUnit] = relationship(lazy="selectin")
    designation: Mapped[Designation] = relationship(lazy="selectin")
    location: Mapped[Location] = relationship(lazy="selectin")
    reviewed_by: Mapped[User] = relationship(foreign_keys=[reviewed_by_id])
    created_employee: Mapped["Employee"] = relationship(
        foreign_keys=[created_employee_id]
    )
    documents: Mapped[list["SubmissionDocument"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class SubmissionDocument(Base):
    __tablename__ = "submission_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("employee_submissions.id"), index=True
    )

    doc_type: Mapped[str] = mapped_column(String(60))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verifier_remark: Mapped[str] = mapped_column(String(255), default="")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    submission: Mapped[EmployeeSubmission] = relationship(back_populates="documents")


# ============================================================================
# Audit log
# ============================================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    actor_email: Mapped[str] = mapped_column(String(160), default="")
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="", index=True)
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    summary: Mapped[str] = mapped_column(String(400), default="")
    detail_json: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


# ============================================================================
# System configuration (Admin > Settings)
# ============================================================================
class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
