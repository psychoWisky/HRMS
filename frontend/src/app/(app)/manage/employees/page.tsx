"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Camera,
  Copy,
  History,
  KeyRound,
  Pencil,
  Power,
  TrendingUp,
  UserPlus,
} from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { OrgUnitPicker } from "@/components/OrgUnitPicker";
import { OrgUnitSelect } from "@/components/OrgUnitSelect";
import { fmtDate, titleize } from "@/lib/format";
import {
  Avatar,
  Empty,
  SectionTitle,
  Spinner,
  StatusBadge,
} from "@/components/ui";
import { SearchableSelect } from "@/components/SearchableSelect";

interface EmployeeRow {
  id: number;
  hrms_employee_id: string;
  full_name: string;
  designation: string | null;
  designation_id: number | null;
  organization: string | null;
  organization_id: number | null;
  org_unit_id: number | null;
  location: string | null;
  official_email: string;
  phone: string;
  photo_url: string;
  pay_scale?: string;
  reports_to: string | null;
  employment_status: string;
  is_active: boolean;
}

interface Option {
  id: number;
  name: string;
}

interface Credential {
  employee_id: number;
  hrms_employee_id: string;
  login_email: string;
  temporary_password: string;
  note: string;
}

interface HistoryEntry {
  id: number;
  event_type: string;
  previous_designation: string | null;
  new_designation: string | null;
  previous_organization: string | null;
  new_organization: string | null;
  previous_employee_code: string;
  new_employee_code: string;
  effective_date: string;
  remarks: string;
  created_at: string;
}

const BLANK = {
  full_name: "",
  official_email: "",
  phone: "",
  gender: "",
  date_of_birth: "",
  date_of_joining: "",
  org_unit_id: "" as string,
  location_id: "",
  designation_id: "",
  pay_scale: "",
  role_code: "hr_admin",
};

const PROMOTE_BLANK = {
  new_designation_id: "",
  new_org_unit_id: "" as string,
  new_pay_scale: "",
  promotion_date: "",
  new_position_joining_date: "",
  remarks: "",
};

export default function ManageEmployeesPage() {
  const { can } = useAuth();
  const { push } = useToast();

  const [orgId, setOrgId] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "1000" });
    if (orgId) params.set("org_unit_id", orgId);
    if (includeInactive) params.set("include_inactive", "true");
    return `/api/employees?${params.toString()}`;
  }, [orgId, includeInactive]);

  const { data, loading, reload } = useApi<EmployeeRow[]>(path);
  const { data: locations } = useApi<Option[]>("/api/locations");
  const { data: designations } = useApi<Option[]>("/api/designations");

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<EmployeeRow | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [busy, setBusy] = useState(false);
  const [credential, setCredential] = useState<Credential | null>(null);

  const [promoting, setPromoting] = useState<EmployeeRow | null>(null);
  const [promoteForm, setPromoteForm] = useState({ ...PROMOTE_BLANK });

  const [historyFor, setHistoryFor] = useState<EmployeeRow | null>(null);
  const { data: history, loading: historyLoading } = useApi<HistoryEntry[]>(
    historyFor ? `/api/employees/${historyFor.id}/history` : null
  );

  const photoInputRef = useRef<HTMLInputElement>(null);
  const [photoTarget, setPhotoTarget] = useState<number | null>(null);

  const canCreate = can(P.employeeCreate);
  const canEdit = can(P.employeeEdit);
  const canDeactivate = can(P.employeeDelete);
  const canReset = can(P.userResetPassword);
  const canPromote = can(P.employeePromote);

  function numeric(v: string) {
    return v ? Number(v) : null;
  }

  async function createEmployee() {
    setBusy(true);
    try {
      const cred = await api.post<Credential>("/api/employees", {
        full_name: form.full_name,
        official_email: form.official_email,
        phone: form.phone,
        gender: form.gender,
        date_of_birth: form.date_of_birth || null,
        date_of_joining: form.date_of_joining || null,
        org_unit_id: numeric(form.org_unit_id),
        location_id: numeric(form.location_id),
        designation_id: numeric(form.designation_id),
        pay_scale: form.pay_scale,
        create_login: true,
        role_code: form.role_code,
      });
      setCreateOpen(false);
      setForm({ ...BLANK });
      setCredential(cred);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not create employee");
    } finally {
      setBusy(false);
    }
  }

  async function saveEdit() {
    if (!editing) return;
    setBusy(true);
    try {
      await api.put(`/api/employees/${editing.id}`, {
        full_name: form.full_name,
        official_email: form.official_email,
        phone: form.phone,
        org_unit_id: numeric(form.org_unit_id),
        location_id: numeric(form.location_id),
        designation_id: numeric(form.designation_id),
        pay_scale: form.pay_scale,
      });
      push("success", "Employee updated");
      setEditing(null);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(row: EmployeeRow) {
    try {
      await api.post(
        `/api/employees/${row.id}/activation?is_active=${!row.is_active}`
      );
      push("success", `${row.full_name} ${row.is_active ? "deactivated" : "activated"}`);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  async function issueCredentials(row: EmployeeRow) {
    try {
      const cred = await api.post<Credential>(
        `/api/employees/${row.id}/credentials`
      );
      setCredential(cred);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not issue credentials");
    }
  }

  function startPhotoUpload(row: EmployeeRow) {
    setPhotoTarget(row.id);
    photoInputRef.current?.click();
  }

  async function onPhotoChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || photoTarget === null) return;
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.upload(`/api/employees/${photoTarget}/photo`, fd);
      push("success", "Photo updated");
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setPhotoTarget(null);
    }
  }

  async function submitPromotion() {
    if (!promoting) return;
    setBusy(true);
    try {
      await api.post(`/api/employees/${promoting.id}/promote`, {
        new_designation_id: promoteForm.new_designation_id
          ? Number(promoteForm.new_designation_id)
          : null,
        new_org_unit_id: promoteForm.new_org_unit_id
          ? Number(promoteForm.new_org_unit_id)
          : null,
        new_pay_scale: promoteForm.new_pay_scale || null,
        promotion_date: promoteForm.promotion_date || null,
        new_position_joining_date: promoteForm.new_position_joining_date || null,
        remarks: promoteForm.remarks,
      });
      push("success", `${promoting.full_name} promoted`);
      setPromoting(null);
      setPromoteForm({ ...PROMOTE_BLANK });
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Promotion failed");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<EmployeeRow>[] = [
    {
      header: "Employee",
      value: (r) => `${r.full_name} ${r.hrms_employee_id} ${r.official_email}`,
      cell: (r) => (
        <div className="flex items-center gap-3">
          <div className="relative">
            <Avatar name={r.full_name} src={r.photo_url} size={38} />
            {canEdit && (
              <button
                onClick={() => startPhotoUpload(r)}
                className="absolute -bottom-1 -right-1 rounded-full border border-[var(--color-line)] bg-white p-1 text-[var(--color-green)] shadow-sm"
                title="Update photo"
              >
                <Camera size={11} /> <span className="text-[10px]">Photo</span>
              </button>
            )}
          </div>
          <div className="min-w-0">
            <Link
              href={`/directory/${r.id}`}
              className="block truncate font-semibold text-[var(--color-ink)] hover:underline"
            >
              {r.full_name}
            </Link>
            <span className="font-mono text-xs text-[var(--color-ink-faint)]">
              {r.hrms_employee_id}
            </span>
          </div>
        </div>
      ),
    },
    {
      header: "Designation",
      value: (r) => r.designation ?? "",
      cell: (r) => r.designation ?? "—",
    },
    {
      header: "Establishment/Department",
      value: (r) => `${r.organization ?? ""} ${r.location ?? ""}`,
      cell: (r) => (
        <div>
          <p>{r.organization ?? "—"}</p>
          <p className="text-xs text-[var(--color-ink-faint)]">{r.location ?? ""}</p>
        </div>
      ),
    },
    {
      header: "Pay Scale",
      value: (r) => r.pay_scale ?? "",
      cell: (r) => r.pay_scale || "—",
    },
    {
      header: "Reports to",
      value: (r) => r.reports_to ?? "",
      cell: (r) => r.reports_to ?? "—",
    },
    {
      header: "Status",
      value: (r) => (r.is_active ? "Active" : "Inactive"),
      cell: (r) => (
        <StatusBadge
          status={r.is_active ? "active" : "cancelled"}
          label={r.is_active ? "Active" : "Inactive"}
        />
      ),
    },
    {
      header: "Actions",
      cell: (r) => (
        <div className="flex max-w-[min(56rem,calc(100vw-3rem))] flex-nowrap gap-1.5 overflow-x-auto whitespace-nowrap pb-0.5">
          {canEdit && (
            <button
              onClick={() => {
                setEditing(r);
                setForm({
                  ...BLANK,
                  full_name: r.full_name,
                  official_email: r.official_email,
                  phone: r.phone,
                  org_unit_id: String(r.org_unit_id ?? r.organization_id ?? ""),
                  designation_id: String(r.designation_id ?? ""),
                  pay_scale: r.pay_scale ?? "",
                });
              }}
              className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--color-line)] px-2 py-1 text-xs text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
              title="Edit"
            >
              <Pencil size={15} /> <span>Edit</span>
            </button>
          )}
          {canPromote && (
            <button
              onClick={() => {
                setPromoting(r);
                setPromoteForm({ ...PROMOTE_BLANK });
              }}
              className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--color-line)] px-2 py-1 text-xs text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
              title="Promote"
            >
              <TrendingUp size={15} /> <span>Promote</span>
            </button>
          )}
          <button
            onClick={() => setHistoryFor(r)}
            className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--color-line)] px-2 py-1 text-xs text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-2)]"
            title="View history / timeline"
          >
            <History size={15} /> <span>History</span>
          </button>
          {canReset && (
            <button
              onClick={() => issueCredentials(r)}
              className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--color-line)] px-2 py-1 text-xs text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
              title="Issue / reset credentials"
            >
              <KeyRound size={15} /> <span>Credentials</span>
            </button>
          )}
          {canDeactivate && (
            <button
              onClick={() => toggleActive(r)}
              className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-[var(--color-line)] px-2 py-1 text-xs text-[var(--color-danger)] hover:bg-[#fbf0f0]"
              title={r.is_active ? "Deactivate" : "Activate"}
            >
              <Power size={15} /> <span>{r.is_active ? "Deactivate" : "Activate"}</span>
            </button>
          )}
        </div>
      ),
    },
  ];

  const fields = (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label className="label">Full name *</label>
        <input
          className="input"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
        />
      </div>
      <div>
        <label className="label">Official / login email *</label>
        <input
          className="input"
          type="email"
          value={form.official_email}
          onChange={(e) => setForm({ ...form, official_email: e.target.value })}
        />
      </div>
      <div>
        <label className="label">Phone</label>
        <input
          className="input"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
      </div>
      <div className="sm:col-span-2">
        <label className="label">
          Office / placement <span style={{ color: "var(--color-danger)" }}>*</span>
        </label>
        <OrgUnitPicker
          value={form.org_unit_id ? Number(form.org_unit_id) : null}
          onChange={(id) => setForm({ ...form, org_unit_id: id ? String(id) : "" })}
          required
        />
        <p className="mt-1 text-xs text-[var(--color-ink-faint)]">
          The Employee ID uses the Establishment’s short code:
          AVFU/&lt;establishment&gt;/&lt;dept|GEN&gt;/####
        </p>
      </div>
      <div>
        <label className="label">Designation</label>
        <SearchableSelect
          value={form.designation_id}
          onChange={(value) => setForm({ ...form, designation_id: value })}
          placeholder="Not assigned"
          searchPlaceholder="Search designations..."
          options={(designations ?? []).map((d) => ({ value: String(d.id), label: d.name }))}
        />
      </div>
      <div>
        <label className="label">Pay Scale</label>
        <input
          className="input"
          value={form.pay_scale}
          onChange={(e) => setForm({ ...form, pay_scale: e.target.value })}
          placeholder="e.g. Level 10 (56,100 - 1,77,500)"
        />
      </div>
      {!editing && (
        <>
          <div>
            <label className="label">Campus / Location</label>
            <SearchableSelect
              value={form.location_id}
              onChange={(value) => setForm({ ...form, location_id: value })}
              placeholder="Not assigned"
              searchPlaceholder="Search campuses..."
              options={(locations ?? []).map((l) => ({ value: String(l.id), label: l.name }))}
            />
          </div>
          <div>
            <label className="label">Role</label>
            <SearchableSelect
              value={form.role_code}
              onChange={(value) => setForm({ ...form, role_code: value })}
              searchPlaceholder="Search roles..."
              options={[
                { value: "hr_admin", label: "HR" },
                { value: "admin", label: "Administrator" },
                { value: "department_head", label: "Department Head" },
              ]}
            />
            <p className="mt-1 text-xs text-[var(--color-ink-faint)]">
              Ordinary employees have no login. Assign the department a
              Department Head manages afterwards, from Users &amp; Roles.
            </p>
          </div>
          <div>
            <label className="label">Date of birth</label>
            <input
              className="input"
              type="date"
              value={form.date_of_birth}
              onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Date of joining</label>
            <input
              className="input"
              type="date"
              value={form.date_of_joining}
              onChange={(e) => setForm({ ...form, date_of_joining: e.target.value })}
            />
          </div>
        </>
      )}
    </div>
  );

  return (
    <>
      <input
        ref={photoInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={onPhotoChosen}
      />

      <div className="mb-2 flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          title="Employees"
          subtitle="Create employee records, assign them within the university and issue login credentials."
        />
        {canCreate && (
          <button onClick={() => setCreateOpen(true)} className="btn btn-primary">
            <UserPlus size={18} /> Create employee
          </button>
        )}
      </div>

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No employees match those filters"
        searchPlaceholder="Search name, HRMS ID, email, designation or office"
        toolbar={
          <>
            <OrgUnitSelect
              className="w-auto min-w-[240px]"
              value={orgId ? Number(orgId) : null}
              onChange={(id) => setOrgId(id ? String(id) : "")}
              placeholder="All establishments / departments"
            />
            <label className="flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
              Include inactive
            </label>
          </>
        }
      />

      {/* Create */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Create employee"
        wide
      >
        {fields}
        <p className="mt-4 rounded-xl bg-[var(--color-surface-2)] p-3 text-sm text-[var(--color-ink-soft)]">
          A permanent HRMS Employee ID is generated automatically (using the
          Establishment's Short Form when it has one), and a login account is
          created with a temporary password shown once on the next screen.
        </p>
        <button
          onClick={createEmployee}
          className="btn btn-primary mt-4 w-full"
          disabled={busy || !form.full_name || !form.official_email}
        >
          {busy ? <Spinner /> : "Create employee and issue credentials"}
        </button>
      </Modal>

      {/* Edit */}
      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={`Edit ${editing?.full_name ?? ""}`}
        wide
      >
        {fields}
        <button
          onClick={saveEdit}
          className="btn btn-primary mt-4 w-full"
          disabled={busy}
        >
          {busy ? <Spinner /> : "Save changes"}
        </button>
      </Modal>

      {/* Promote */}
      <Modal
        open={!!promoting}
        onClose={() => setPromoting(null)}
        title={`Promote ${promoting?.full_name ?? ""}`}
        wide
      >
        <p className="mb-4 text-sm text-[var(--color-ink-soft)]">
          Leave a field unset to keep it unchanged. History is always
          preserved — if the new Establishment differs from the current one,
          a new Employee ID is generated automatically and the old one is
          kept in the timeline.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">New designation</label>
            <select
              className="input"
              value={promoteForm.new_designation_id}
              onChange={(e) =>
                setPromoteForm({ ...promoteForm, new_designation_id: e.target.value })
              }
            >
              <option value="">Unchanged</option>
              {(designations ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label">
              New office / placement (leave blank to keep)
            </label>
            <OrgUnitPicker
              value={
                promoteForm.new_org_unit_id
                  ? Number(promoteForm.new_org_unit_id)
                  : null
              }
              onChange={(id) =>
                setPromoteForm({
                  ...promoteForm,
                  new_org_unit_id: id ? String(id) : "",
                })
              }
            />
          </div>
          <div>
            <label className="label">New Pay Scale</label>
            <input
              className="input"
              value={promoteForm.new_pay_scale}
              onChange={(e) =>
                setPromoteForm({ ...promoteForm, new_pay_scale: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label">Promotion date</label>
            <input
              className="input"
              type="date"
              value={promoteForm.promotion_date}
              onChange={(e) =>
                setPromoteForm({ ...promoteForm, promotion_date: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label">Date of joining new position</label>
            <input
              className="input"
              type="date"
              value={promoteForm.new_position_joining_date}
              onChange={(e) =>
                setPromoteForm({
                  ...promoteForm,
                  new_position_joining_date: e.target.value,
                })
              }
            />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Remarks</label>
            <input
              className="input"
              value={promoteForm.remarks}
              onChange={(e) => setPromoteForm({ ...promoteForm, remarks: e.target.value })}
            />
          </div>
        </div>
        <button
          onClick={submitPromotion}
          className="btn btn-primary mt-4 w-full"
          disabled={busy}
        >
          {busy ? <Spinner /> : "Confirm promotion"}
        </button>
      </Modal>

      {/* History / timeline */}
      <Modal
        open={!!historyFor}
        onClose={() => setHistoryFor(null)}
        title={`History — ${historyFor?.full_name ?? ""}`}
      >
        {historyLoading ? (
          <Spinner />
        ) : !history || history.length === 0 ? (
          <Empty message="No history recorded yet" />
        ) : (
          <ol className="space-y-4">
            {history.map((h) => (
              <li key={h.id} className="border-l-2 border-[var(--color-line)] pl-4">
                <p className="text-sm font-semibold text-[var(--color-green)]">
                  {fmtDate(h.effective_date)} · {titleize(h.event_type)}
                </p>
                <div className="mt-1 space-y-0.5 text-sm text-[var(--color-ink-soft)]">
                  {h.previous_designation !== h.new_designation && (
                    <p>
                      Designation: {h.previous_designation ?? "—"} →{" "}
                      <strong>{h.new_designation ?? "—"}</strong>
                    </p>
                  )}
                  {h.previous_organization !== h.new_organization && (
                    <p>
                      Establishment/Department: {h.previous_organization ?? "—"} →{" "}
                      <strong>{h.new_organization ?? "—"}</strong>
                    </p>
                  )}
                  {h.previous_employee_code !== h.new_employee_code &&
                    h.previous_employee_code && (
                      <p>
                        Employee ID:{" "}
                        <span className="font-mono">{h.previous_employee_code}</span>{" "}
                        → <strong className="font-mono">{h.new_employee_code}</strong>
                      </p>
                    )}
                  {h.remarks && <p className="italic">{h.remarks}</p>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </Modal>

      {/* Credentials issued — shown once */}
      <Modal
        open={!!credential}
        onClose={() => setCredential(null)}
        title="Credentials issued"
      >
        {credential && (
          <div className="space-y-4">
            <div className="rounded-xl border-2 border-[var(--color-green)] bg-[var(--color-green-tint)] p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                HRMS Employee ID
              </p>
              <p className="font-mono text-lg font-bold">
                {credential.hrms_employee_id}
              </p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                Login email
              </p>
              <p className="font-mono">{credential.login_email}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                Temporary password
              </p>
              <div className="flex items-center gap-2">
                <p className="font-mono text-lg font-bold">
                  {credential.temporary_password}
                </p>
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(credential.temporary_password);
                    push("success", "Copied");
                  }}
                  className="rounded-lg border border-[var(--color-line)] bg-white p-1.5"
                  title="Copy"
                >
                  <Copy size={15} />
                </button>
              </div>
            </div>
            <p className="text-sm text-[var(--color-ink-soft)]">{credential.note}</p>
            <p className="text-sm text-[var(--color-ink-faint)]">
              The employee will be required to change this password at first
              sign-in.
            </p>
            <button
              onClick={() => setCredential(null)}
              className="btn btn-primary w-full"
            >
              Done
            </button>
          </div>
        )}
      </Modal>
    </>
  );
}
