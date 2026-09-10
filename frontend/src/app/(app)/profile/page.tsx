"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Lock, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useToast } from "@/components/Toast";
import { KYC_LABEL, fmtDate, kycTone } from "@/lib/format";
import {
  Avatar,
  Empty,
  Field,
  MotionCard,
  SectionTitle,
  Skeleton,
  Spinner,
  StatusBadge,
} from "@/components/ui";

interface EmployeeDetail {
  id: number;
  hrms_employee_id: string;
  full_name: string;
  designation: string | null;
  organization: string | null;
  organization_path: string;
  location: string | null;
  official_email: string;
  phone: string;
  gender: string;
  date_of_birth: string | null;
  date_of_joining: string | null;
  post_label: string | null;
  reports_to: string | null;
  employment_status: string;
  kyc_status: string | null;
  login_email: string | null;
  role_code: string | null;
}

export default function ProfilePage() {
  const { data, loading, reload } = useApi<EmployeeDetail>("/api/employees/me");
  const { push } = useToast();
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data) setPhone(data.phone ?? "");
  }, [data]);

  async function save() {
    setSaving(true);
    try {
      await api.put("/api/employees/me", { phone });
      push("success", "Contact details updated");
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Skeleton className="h-96" />;
  if (!data) return <Empty message="Profile unavailable" />;

  return (
    <>
      <SectionTitle
        title="My Profile"
        subtitle="Your official HRMS record. Designation, post, organisation and reporting authority are maintained by Admin/HR."
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <MotionCard className="lg:col-span-2">
          <div className="mb-5 flex items-center gap-4">
            <Avatar name={data.full_name} size={64} />
            <div>
              <p className="text-xl font-bold">{data.full_name}</p>
              <p className="text-[var(--color-ink-soft)]">
                {data.designation ?? "Designation not assigned"}
              </p>
              <p className="mt-1 font-mono text-sm text-[var(--color-ink-faint)]">
                {data.hrms_employee_id}
              </p>
            </div>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="HRMS Employee ID" value={data.hrms_employee_id} mono />
            <Field label="Employment Status" value={data.employment_status} />
            <Field label="Designation" value={data.designation} />
            <Field label="Sanctioned Post" value={data.post_label} />
            <Field label="Organisation" value={data.organization} />
            <Field label="Campus / Location" value={data.location} />
            <Field label="Reporting Authority" value={data.reports_to} />
            <Field label="Date of Joining" value={fmtDate(data.date_of_joining)} />
            <Field label="Gender" value={data.gender} />
            <Field label="Date of Birth" value={fmtDate(data.date_of_birth)} />
          </div>

          <div className="mt-5 rounded-xl bg-[var(--color-surface-2)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
              Organisational position
            </p>
            <p className="mt-1 text-[15px]">{data.organization_path || "—"}</p>
          </div>

          <p className="mt-4 flex items-start gap-2 text-sm text-[var(--color-ink-faint)]">
            <Lock size={15} className="mt-0.5 shrink-0" />
            These fields are official HRMS data. Contact the HRMS administrator if
            anything needs correcting.
          </p>
        </MotionCard>

        <div className="space-y-5">
          <MotionCard>
            <h3 className="mb-4 text-lg font-bold">Editable contact details</h3>
            <div>
              <label className="label">Phone</label>
              <input
                className="input"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="10-digit mobile number"
              />
            </div>
            <button
              onClick={save}
              className="btn btn-primary mt-4 w-full"
              disabled={saving}
            >
              {saving ? (
                <Spinner />
              ) : (
                <>
                  <Save size={18} /> Save
                </>
              )}
            </button>
          </MotionCard>

          <MotionCard>
            <h3 className="mb-3 text-lg font-bold">Account</h3>
            <div className="space-y-4">
              <Field label="Login Email" value={data.login_email} />
              <Field label="Role" value={data.role_code} />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                  Document Status
                </p>
                <div className="mt-1.5">
                  <StatusBadge
                    status={kycTone(data.kyc_status)}
                    label={KYC_LABEL[data.kyc_status ?? ""] ?? "Not Started"}
                  />
                </div>
              </div>
            </div>
            <Link href="/change-password" className="btn btn-ghost mt-4 w-full">
              Change password
            </Link>
          </MotionCard>
        </div>
      </div>
    </>
  );
}
