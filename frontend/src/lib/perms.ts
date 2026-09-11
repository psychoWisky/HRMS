/** Permission codes, mirroring backend/app/core/permissions.py.
 *
 *  The frontend uses these only to decide what to *render*; every one of
 *  them is independently enforced on the API.
 */
export const P = {
  directoryRead: "directory:read",
  orgRead: "org:read",
  employeeRead: "employee:read",
  reportRead: "report:read",

  profileEditOwn: "profile:edit_own",
  passwordChangeOwn: "password:change_own",

  employeeCreate: "employee:create",
  employeeEdit: "employee:edit",
  employeeDelete: "employee:delete",
  employeePromote: "employee:promote",

  orgCreate: "org:create",
  orgEdit: "org:edit",
  orgDelete: "org:delete",
  structureManage: "structure:manage",

  designationManage: "designation:manage",
  reportingManage: "reporting:manage",

  submissionReview: "submission:review",
  kycVerify: "kyc:verify",
  customFieldManage: "custom_field:manage",

  userManage: "user:manage",
  userResetPassword: "user:reset_password",
  roleManage: "role:manage",

  auditRead: "audit:read",
} as const;
