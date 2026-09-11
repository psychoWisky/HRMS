"""Pydantic request/response models for the AVFU HRMS API."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.models import (
    CustomFieldType,
    DesignationCategory,
    EmploymentStatus,
    KYCStatus,
    OrgUnitKind,
    PositionEventType,
    ReportingType,
    SubmissionStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Auth
# ============================================================================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    full_name: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class CurrentUser(BaseModel):
    id: int
    email: str
    role: str
    role_name: str
    permissions: list[str]
    must_change_password: bool
    employee_id: int | None
    hrms_employee_id: str | None
    full_name: str
    designation: str | None
    org_unit: str | None
    kyc_status: str | None
    # Set only for Department Head accounts: the department they manage.
    managed_org_unit_id: int | None = None
    managed_org_unit_name: str | None = None


# ============================================================================
# Location
# ============================================================================
class LocationBase(BaseModel):
    name: str
    code: str = ""
    address: str = ""
    city: str = ""
    district: str = ""
    state: str = "Assam"
    pincode: str = ""
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    is_active: bool | None = None


class LocationOut(ORMModel, LocationBase):
    id: int
    employee_count: int = 0


# ============================================================================
# Org units (College -> Establishment | Department -> Section/Unit/Cell)
# ============================================================================
class OrgUnitBase(BaseModel):
    kind: OrgUnitKind = OrgUnitKind.section
    sub_kind: str = ""  # section | unit | cell (only for kind=section)
    parent_id: int | None = None
    name: str
    # ID segment: AVFU/<est short_code>/<dept short_code|GEN>/serial
    short_code: str = ""
    code: str = ""
    location_id: int | None = None
    sort_order: int = 0
    is_active: bool = True
    # --- Part A (establishment / department) ---
    head_employee_id: int | None = None
    reporting_authority_text: str = ""
    hrms_contact_name: str = ""
    hrms_contact_designation: str = ""
    hrms_contact_phone: str = ""
    hrms_contact_email: str = ""
    office_email: str = ""
    description: str = ""
    # --- Part C (section) ---
    officer_in_charge_employee_id: int | None = None
    headcount_note: str = ""


class OrgUnitCreate(OrgUnitBase):
    pass


class OrgUnitUpdate(BaseModel):
    kind: OrgUnitKind | None = None
    sub_kind: str | None = None
    parent_id: int | None = None
    name: str | None = None
    short_code: str | None = None
    code: str | None = None
    location_id: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    head_employee_id: int | None = None
    reporting_authority_text: str | None = None
    hrms_contact_name: str | None = None
    hrms_contact_designation: str | None = None
    hrms_contact_phone: str | None = None
    hrms_contact_email: str | None = None
    office_email: str | None = None
    description: str | None = None
    officer_in_charge_employee_id: int | None = None
    headcount_note: str | None = None


class OrgUnitOut(ORMModel):
    id: int
    kind: OrgUnitKind
    sub_kind: str
    parent_id: int | None
    parent_name: str | None = None
    college_id: int | None = None
    college_name: str | None = None
    name: str
    short_code: str
    code: str
    location_id: int | None
    location_name: str | None = None
    sort_order: int
    is_active: bool
    path: str = ""
    head_employee_id: int | None = None
    head_name: str | None = None
    reporting_authority_text: str = ""
    hrms_contact_name: str = ""
    hrms_contact_designation: str = ""
    hrms_contact_phone: str = ""
    hrms_contact_email: str = ""
    office_email: str = ""
    description: str = ""
    officer_in_charge_employee_id: int | None = None
    officer_in_charge_name: str | None = None
    headcount_note: str = ""
    direct_employee_count: int = 0
    employee_count: int = 0
    sanctioned_count: int = 0
    child_count: int = 0


class OrgUnitNode(BaseModel):
    """One node of the navigable hierarchy tree."""

    id: int
    name: str
    short_code: str
    kind: OrgUnitKind
    sub_kind: str = ""
    location_name: str | None = None
    head_name: str | None = None
    head_id: int | None = None
    officer_in_charge_name: str | None = None
    direct_employee_count: int = 0
    total_employee_count: int = 0
    sanctioned_count: int = 0
    is_active: bool = True
    children: list["OrgUnitNode"] = []


class OfficeDetail(OrgUnitOut):
    """The office page bundle: Part A (this row) + Part B posts + Part C sections."""

    part_b: list["PostOut"] = []
    part_c: list[OrgUnitOut] = []


# ============================================================================
# Designation & Post
# ============================================================================
class DesignationBase(BaseModel):
    name: str
    short_name: str = ""
    category: DesignationCategory = DesignationCategory.administrative
    rank_level: int = 50
    description: str = ""
    is_active: bool = True


class DesignationCreate(DesignationBase):
    pass


class DesignationUpdate(BaseModel):
    name: str | None = None
    short_name: str | None = None
    category: DesignationCategory | None = None
    rank_level: int | None = None
    description: str | None = None
    is_active: bool | None = None


class DesignationOut(ORMModel, DesignationBase):
    id: int
    sanctioned_total: int = 0
    occupied_total: int = 0
    vacant_total: int = 0
    employee_count: int = 0


class PostBase(BaseModel):
    org_unit_id: int
    designation_id: int
    level_no: int = 0
    sanctioned_count: int = 0
    reported_vacant_count: int = 0
    level_label: str = ""
    reports_to_note: str = ""
    reports_to_designation_id: int | None = None
    remarks: str = ""
    is_active: bool = True


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    org_unit_id: int | None = None
    designation_id: int | None = None
    level_no: int | None = None
    sanctioned_count: int | None = None
    reported_vacant_count: int | None = None
    level_label: str | None = None
    reports_to_note: str | None = None
    reports_to_designation_id: int | None = None
    remarks: str | None = None
    is_active: bool | None = None


class PostOut(ORMModel):
    id: int
    org_unit_id: int
    org_unit_name: str = ""
    designation_id: int
    designation_name: str = ""
    level_no: int = 0
    sanctioned_count: int
    occupied_count: int = 0
    vacant_count: int = 0
    # Employees in post beyond the sanctioned strength. Vacancy never goes
    # negative, so this is reported separately.
    over_strength_count: int = 0
    reported_vacant_count: int
    level_label: str
    reports_to_note: str
    reports_to_designation_id: int | None
    reports_to_designation_name: str | None = None
    remarks: str
    is_active: bool


# ============================================================================
# Employee
# ============================================================================
class EmployeeCreate(BaseModel):
    full_name: str
    hrms_employee_id: str | None = None  # auto-generated when omitted
    gender: str = ""
    date_of_birth: date | None = None
    official_email: str = ""
    phone: str = ""
    photo_url: str = ""
    org_unit_id: int | None = None
    location_id: int | None = None
    designation_id: int | None = None
    post_id: int | None = None
    pay_scale: str = ""
    date_of_joining: date | None = None
    employment_status: EmploymentStatus = EmploymentStatus.active
    remarks: str = ""

    create_login: bool = False
    login_email: EmailStr | None = None
    role_code: str = "hr_admin"
    initial_password: str | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    official_email: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    org_unit_id: int | None = None
    location_id: int | None = None
    designation_id: int | None = None
    post_id: int | None = None
    pay_scale: str | None = None
    date_of_joining: date | None = None
    employment_status: EmploymentStatus | None = None
    is_active: bool | None = None
    remarks: str | None = None


class EmployeePhotoUpdate(BaseModel):
    photo_url: str


class SelfProfileUpdate(BaseModel):
    phone: str | None = None
    photo_url: str | None = None


class PromotionRequest(BaseModel):
    new_designation_id: int | None = None
    new_org_unit_id: int | None = None
    new_post_id: int | None = None
    new_pay_scale: str | None = None
    promotion_date: date | None = None
    new_position_joining_date: date | None = None
    remarks: str = ""


class PositionHistoryOut(ORMModel):
    id: int
    event_type: PositionEventType
    previous_designation: str | None = None
    new_designation: str | None = None
    previous_organization: str | None = None
    new_organization: str | None = None
    previous_employee_code: str = ""
    new_employee_code: str = ""
    previous_pay_scale: str = ""
    new_pay_scale: str = ""
    promotion_date: date | None = None
    new_position_joining_date: date | None = None
    effective_date: date
    remarks: str = ""
    created_at: datetime


class EmployeeSummary(ORMModel):
    """The shape shown in the university-wide directory."""

    id: int
    hrms_employee_id: str
    full_name: str
    college: str | None = None
    college_id: int | None = None
    department: str | None = None
    department_id: int | None = None
    establishment: str | None = None
    establishment_id: int | None = None
    designation: str | None = None
    designation_id: int | None = None
    # ``organization`` / ``organization_id`` are kept as field names for
    # frontend compatibility but now carry the employee's OrgUnit.
    organization: str | None = None
    org_unit_id: int | None = None
    org_unit_id: int | None = None
    org_unit_kind: OrgUnitKind | None = None
    organization_path: str = ""
    location: str | None = None
    official_email: str = ""
    phone: str = ""
    photo_url: str = ""
    reports_to: str | None = None
    reports_to_id: int | None = None
    employment_status: EmploymentStatus
    is_active: bool


class EmployeeDetail(EmployeeSummary):
    gender: str = ""
    date_of_birth: date | None = None
    date_of_joining: date | None = None
    post_id: int | None = None
    post_label: str | None = None
    location_id: int | None = None
    pay_scale: str = ""
    remarks: str = ""
    kyc_status: KYCStatus | None = None
    has_login: bool = False
    login_email: str | None = None
    role_code: str | None = None
    user_is_active: bool | None = None
    direct_reports: list[EmployeeSummary] = []
    reporting_chain: list[EmployeeSummary] = []
    history: list[PositionHistoryOut] = []


class CredentialIssued(BaseModel):
    """Returned once, immediately after Admin creates or resets an account.

    The temporary password is shown a single time and never stored in
    plaintext, so it cannot be retrieved again.
    """

    employee_id: int
    hrms_employee_id: str
    login_email: str
    temporary_password: str
    must_change_password: bool = True
    note: str = (
        "Communicate this temporary password to the employee through the approved "
        "process. It cannot be retrieved again."
    )


# ============================================================================
# Reporting hierarchy
# ============================================================================
class ReportingCreate(BaseModel):
    employee_id: int
    reports_to_id: int
    relationship_type: ReportingType = ReportingType.administrative
    is_primary: bool = True
    effective_from: date | None = None


class ReportingOut(ORMModel):
    id: int
    employee_id: int
    employee_name: str = ""
    reports_to_id: int
    reports_to_name: str = ""
    reports_to_designation: str | None = None
    relationship_type: ReportingType
    is_primary: bool
    effective_from: date | None
    effective_to: date | None


class ReportingStructure(BaseModel):
    employee: EmployeeSummary
    reports_to: EmployeeSummary | None = None
    additional_authorities: list[EmployeeSummary] = []
    reporting_chain: list[EmployeeSummary] = []
    direct_reports: list[EmployeeSummary] = []


# ============================================================================
# KYC
# ============================================================================
class KYCInfoUpdate(BaseModel):
    father_name: str | None = None
    mother_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    marital_status: str | None = None
    nationality: str | None = None
    category: str | None = None
    aadhaar_number: str | None = None
    pan_number: str | None = None
    personal_email: str | None = None
    contact_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    permanent_address: str | None = None
    present_address: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None


class KYCDocumentOut(ORMModel):
    id: int
    doc_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    is_verified: bool
    verifier_remark: str
    uploaded_at: datetime


class KYCHistoryOut(ORMModel):
    id: int
    action: str
    from_status: str
    to_status: str
    actor_name: str
    remark: str
    created_at: datetime


class KYCOut(ORMModel):
    id: int
    employee_id: int
    employee_name: str = ""
    hrms_employee_id: str = ""
    organization: str | None = None
    designation: str | None = None
    status: KYCStatus

    father_name: str = ""
    mother_name: str = ""
    date_of_birth: date | None = None
    gender: str = ""
    blood_group: str = ""
    marital_status: str = ""
    nationality: str = ""
    category: str = ""
    aadhaar_number: str = ""
    pan_number: str = ""
    personal_email: str = ""
    contact_phone: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    permanent_address: str = ""
    present_address: str = ""
    bank_name: str = ""
    bank_account_number: str = ""
    bank_ifsc: str = ""

    submitted_at: datetime | None = None
    verified_at: datetime | None = None
    verified_by_name: str | None = None
    verifier_remark: str = ""
    documents: list[KYCDocumentOut] = []
    history: list[KYCHistoryOut] = []
    can_edit: bool = False


class KYCDecision(BaseModel):
    remark: str = ""


class KYCDocumentVerify(BaseModel):
    is_verified: bool
    remark: str = ""


# ============================================================================
# Configurable employee custom fields & document requirements
# ============================================================================
class CustomFieldCreate(BaseModel):
    key: str = Field(min_length=1, max_length=60)
    label: str
    field_type: CustomFieldType = CustomFieldType.text
    options: list[str] = []
    is_required: bool = False
    org_unit_id: int | None = None
    help_text: str = ""
    sort_order: int = 0


class CustomFieldUpdate(BaseModel):
    label: str | None = None
    field_type: CustomFieldType | None = None
    options: list[str] | None = None
    is_required: bool | None = None
    org_unit_id: int | None = None
    help_text: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CustomFieldOut(BaseModel):
    id: int
    key: str
    label: str
    field_type: CustomFieldType
    options: list[str] = []
    is_required: bool
    org_unit_id: int | None = None
    org_unit_name: str | None = None
    help_text: str
    sort_order: int
    is_active: bool


class CustomFieldValueIn(BaseModel):
    field_id: int
    value: str = ""


class CustomFieldValueOut(BaseModel):
    field_id: int
    key: str
    label: str
    field_type: CustomFieldType
    value: str = ""


class CustomDocumentRequirementCreate(BaseModel):
    label: str
    org_unit_id: int | None = None
    is_required: bool = True


class CustomDocumentRequirementUpdate(BaseModel):
    label: str | None = None
    org_unit_id: int | None = None
    is_required: bool | None = None
    is_active: bool | None = None


class CustomDocumentRequirementOut(BaseModel):
    id: int
    label: str
    org_unit_id: int | None = None
    org_unit_name: str | None = None
    is_required: bool
    is_active: bool


# ============================================================================
# Public new-employee submissions
# ============================================================================
class PublicOption(BaseModel):
    """Minimal reference data safe to expose on the open form."""

    id: int
    name: str
    group: str = ""


class SubmissionInfo(BaseModel):
    """Fields the applicant fills in on the public form."""

    full_name: str = Field(min_length=2, max_length=160)
    email: str = ""
    phone: str = ""
    gender: str = ""
    date_of_birth: date | None = None
    org_unit_id: int | None = None
    designation_id: int | None = None
    location_id: int | None = None
    date_of_joining: date | None = None
    father_name: str = ""
    mother_name: str = ""
    blood_group: str = ""
    marital_status: str = ""
    nationality: str = "Indian"
    category: str = ""
    aadhaar_number: str = ""
    pan_number: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    permanent_address: str = ""
    present_address: str = ""
    bank_name: str = ""
    bank_account_number: str = ""
    bank_ifsc: str = ""


class SubmissionUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    org_unit_id: int | None = None
    designation_id: int | None = None
    location_id: int | None = None
    date_of_joining: date | None = None
    father_name: str | None = None
    mother_name: str | None = None
    blood_group: str | None = None
    marital_status: str | None = None
    nationality: str | None = None
    category: str | None = None
    aadhaar_number: str | None = None
    pan_number: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    permanent_address: str | None = None
    present_address: str | None = None
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None


class SubmissionDocumentOut(ORMModel):
    id: int
    doc_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    is_verified: bool
    verifier_remark: str
    uploaded_at: datetime


class SubmissionCreated(BaseModel):
    """Returned once, when the applicant starts a submission."""

    reference_code: str
    status: SubmissionStatus
    note: str = (
        "Keep this reference code safe — it is the only way to add documents "
        "or check the status of this submission later."
    )


class SubmissionPublicOut(BaseModel):
    """What the applicant themselves can see."""

    reference_code: str
    status: SubmissionStatus
    full_name: str
    email: str
    phone: str
    gender: str
    date_of_birth: date | None
    org_unit_id: int | None
    org_unit: str | None
    designation_id: int | None
    designation: str | None
    location_id: int | None
    location: str | None
    date_of_joining: date | None
    father_name: str
    mother_name: str
    blood_group: str
    marital_status: str
    nationality: str
    category: str
    aadhaar_number: str
    pan_number: str
    emergency_contact_name: str
    emergency_contact_phone: str
    permanent_address: str
    present_address: str
    bank_name: str
    bank_account_number: str
    bank_ifsc: str
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewer_remark: str
    documents: list[SubmissionDocumentOut] = []
    can_edit: bool = False
    hrms_employee_id: str | None = None


class SubmissionAdminOut(SubmissionPublicOut):
    """Everything HR sees while reviewing."""

    id: int
    created_at: datetime
    submitter_ip: str = ""
    reviewed_by_name: str | None = None
    created_employee_id: int | None = None


class SubmissionDecision(BaseModel):
    remark: str = ""


class SubmissionApproval(BaseModel):
    """HR confirms the placement while admitting the applicant."""

    remark: str = ""
    org_unit_id: int | None = None
    designation_id: int | None = None
    location_id: int | None = None
    post_id: int | None = None
    reports_to_id: int | None = None
    hrms_employee_id: str | None = None
    date_of_joining: date | None = None


# ============================================================================
# Users & roles
# ============================================================================
class UserOut(ORMModel):
    id: int
    email: str
    role_code: str = ""
    role_name: str = ""
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None = None
    created_at: datetime
    employee_id: int | None = None
    employee_name: str | None = None
    hrms_employee_id: str | None = None
    managed_org_unit_id: int | None = None
    managed_org_unit_name: str | None = None


class UserRoleUpdate(BaseModel):
    role_code: str


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserScopeUpdate(BaseModel):
    """Assigns the one department a Department Head account may manage."""

    managed_org_unit_id: int | None = None


class PermissionOut(ORMModel):
    id: int
    code: str
    group: str
    description: str


class RoleOut(ORMModel):
    id: int
    code: str
    name: str
    description: str
    is_system: bool
    is_active: bool
    permissions: list[str] = []
    user_count: int = 0
    is_hidden: bool = False


class RoleCreate(BaseModel):
    code: str
    name: str
    description: str = ""
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    permissions: list[str] | None = None


# ============================================================================
# Dashboard & reports
# ============================================================================
class CountItem(BaseModel):
    label: str
    count: int
    extra: int | None = None


class AdminDashboard(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    total_organizations: int
    total_locations: int
    total_designations: int
    sanctioned_posts: int
    occupied_posts: int
    vacant_posts: int
    kyc_not_started: int
    kyc_pending: int
    kyc_verified: int
    kyc_rejected: int
    submissions_awaiting_review: int = 0
    submissions_approved: int = 0
    submissions_rejected: int = 0
    by_location: list[CountItem]
    by_organization: list[CountItem]
    by_designation: list[CountItem]


class EmployeeDashboard(BaseModel):
    hrms_employee_id: str
    full_name: str
    designation: str | None
    org_unit: str | None
    organization_path: str
    location: str | None
    reports_to: str | None
    reports_to_designation: str | None
    direct_reports_count: int
    kyc_status: KYCStatus
    kyc_remark: str = ""
    date_of_joining: date | None
    must_change_password: bool


class AuditLogOut(ORMModel):
    id: int
    actor_email: str
    action: str
    entity_type: str
    entity_id: str
    summary: str
    ip_address: str
    created_at: datetime



OrgUnitNode.model_rebuild()
OfficeDetail.model_rebuild()
