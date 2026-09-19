"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  BadgeCheck,
  CheckCircle2,
  Eye,
  FileText,
  RotateCcw,
  UserPlus,
  XCircle,
} from "lucide-react";
import { ApiError, api, downloadFile } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { OrgUnitSelect } from "@/components/OrgUnitSelect";
import { fmtBytes, fmtDateTime, titleize } from "@/lib/format";
import {
  Empty,
  Field,
  SectionTitle,
  Spinner,
  StatusBadge,
} from "@/components/ui";

interface SubmissionDoc {
  id: number;
  doc_type: string;
  original_filename: string;
  size_bytes: number;
  is_verified: boolean;
  verifier_remark: string;
  uploaded_at: string;
}

interface Submission {
  id: number;
  reference_code: string;
  status: string;
  full_name: string;
  email: string;
  phone: string;
  gender: string;
  date_of_birth: string | null;
  date_of_joining_aau_avfu: string | null;
  date_of_joining_present_post: string | null;
  expected_date_of_retirement: string | null;
  org_unit_id: number | null;
  org_unit: string | null;
  designation_id: number | null;
  designation: string | null;
  location_id: number | null;
  location: string | null;
  date_of_joining: string | null;
  father_name: string;
  mother_name: string;
  blood_group: string;
  marital_status: string;
  nationality: string;
  category: string;
  aadhaar_number: string;
  pan_number: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  permanent_address: string;
  present_address: string;
  bank_name: string;
  bank_account_number: string;
  bank_ifsc: string;
  submitted_at: string | null;
  reviewed_at: string | null;
  reviewed_by_name: string | null;
  reviewer_remark: string;
  documents: SubmissionDoc[];
  created_at: string;
  submitter_ip: string;
  created_employee_id: number | null;
  hrms_employee_id: string | null;
}

interface Option {
  id: number;
  name: string;
}

interface EmployeeOption {
  id: number;
  full_name: string;
  designation: string | null;
}

const FILTERS = [
  { key: "", label: "All active" },
  { key: "submitted", label: "New" },
  { key: "under_review", label: "Under review" },
  { key: "resubmission_required", label: "Awaiting correction" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
  { key: "draft", label: "Drafts" },
];

function tone(status: string): string {
  switch (status) {
    case "approved":
      return "approved";
    case "rejected":
      return "rejected";
    case "submitted":
    case "under_review":
    case "resubmission_required":
      return "pending";
    default:
      return "cancelled";
  }
}

export default function SubmissionsPage() {
  const [status, setStatus] = useState("submitted");
  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "500" });
    if (status) params.set("submission_status", status);
    return `/api/submissions?${params.toString()}`;
  }, [status]);

  const { data, loading, reload } = useApi<Submission[]>(path);
  const { data: designations } = useApi<Option[]>("/api/designations");
  const { data: locations } = useApi<Option[]>("/api/locations");
  const { data: employees } = useApi<EmployeeOption[]>("/api/directory?limit=1000");
  const { push } = useToast();

  const [open, setOpen] = useState<Submission | null>(null);
  const [remark, setRemark] = useState("");
  const [busy, setBusy] = useState(false);

  // Placement HR confirms while admitting the applicant.
  const [placement, setPlacement] = useState({
    org_unit_id: "",
    designation_id: "",
    location_id: "",
    reports_to_id: "",
  });

  function openReview(row: Submission) {
    setOpen(row);
    setRemark("");
    setPlacement({
      org_unit_id: String(row.org_unit_id ?? ""),
      designation_id: String(row.designation_id ?? ""),
      location_id: String(row.location_id ?? ""),
      reports_to_id: "",
    });
  }

  async function act(action: string, label: string) {
    if (!open) return;
    setBusy(true);
    try {
      const updated = await api.post<Submission>(
        `/api/submissions/${open.id}/${action}`,
        { remark }
      );
      push("success", label);
      setOpen(updated);
      setRemark("");
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!open) return;
    setBusy(true);
    try {
      const updated = await api.post<Submission>(
        `/api/submissions/${open.id}/approve`,
        {
          remark,
          org_unit_id: placement.org_unit_id
            ? Number(placement.org_unit_id)
            : null,
          designation_id: placement.designation_id
            ? Number(placement.designation_id)
            : null,
          location_id: placement.location_id ? Number(placement.location_id) : null,
          reports_to_id: placement.reports_to_id
            ? Number(placement.reports_to_id)
            : null,
        }
      );
      push("success", `Admitted as ${updated.hrms_employee_id}`);
      setOpen(updated);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Approval failed");
    } finally {
      setBusy(false);
    }
  }

  async function verifyDoc(doc: SubmissionDoc, verified: boolean) {
    if (!open) return;
    try {
      await api.post(
        `/api/submissions/${open.id}/documents/${doc.id}/verify?is_verified=${verified}`,
        { remark: "" }
      );
      const refreshed = await api.get<Submission>(`/api/submissions/${open.id}`);
      setOpen(refreshed);
      push("success", verified ? "Document marked checked" : "Mark removed");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  const columns: Column<Submission>[] = [
    {
      header: "Reference",
      value: (r) => r.reference_code,
      cell: (r) => (
        <span className="font-mono text-xs font-semibold">{r.reference_code}</span>
      ),
    },
    {
      header: "Applicant",
      value: (r) => r.full_name,
      cell: (r) => (
        <div>
          <p className="font-semibold">{r.full_name}</p>
          <p className="text-xs text-[var(--color-ink-faint)]">{r.email || r.phone}</p>
        </div>
      ),
    },
    {
      header: "Applying to",
      value: (r) => r.org_unit ?? "",
      cell: (r) => (
        <div className="text-sm">
          <p>{r.org_unit ?? "—"}</p>
          <p className="text-xs text-[var(--color-ink-faint)]">
            {r.designation ?? "—"}
          </p>
        </div>
      ),
    },
    {
      header: "Docs",
      value: (r) => r.documents.length,
      cell: (r) => r.documents.length,
    },
    {
      header: "Submitted",
      value: (r) => r.submitted_at ?? "",
      cell: (r) => <span className="text-sm">{fmtDateTime(r.submitted_at)}</span>,
    },
    {
      header: "Status",
      value: (r) => r.status,
      cell: (r) => <StatusBadge status={tone(r.status)} label={titleize(r.status)} />,
    },
    {
      header: "HRMS ID",
      value: (r) => r.hrms_employee_id ?? "",
      cell: (r) =>
        r.created_employee_id ? (
          <Link
            href={`/directory/${r.created_employee_id}`}
            className="font-mono text-xs text-[var(--color-green)] hover:underline"
          >
            {r.hrms_employee_id}
          </Link>
        ) : (
          <span className="text-[var(--color-ink-faint)]">—</span>
        ),
    },
    {
      header: "",
      cell: (r) => (
        <button
          onClick={() => openReview(r)}
          className="btn btn-ghost px-3 py-1.5 text-sm"
        >
          <Eye size={16} /> Review
        </button>
      ),
    },
  ];

  const reviewable =
    open && ["submitted", "under_review"].includes(open.status);

  return (
    <>
      <SectionTitle
        title="New Employee Submissions"
        subtitle="Documents sent through the public form at /submit. Approving a submission is what creates the employee record and issues the HRMS Employee ID."
      />

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No submissions in this state"
        searchPlaceholder="Search reference, applicant, office or status"
        toolbar={
          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setStatus(f.key)}
                className="rounded-full border px-3.5 py-1.5 text-sm font-semibold transition-colors"
                style={{
                  borderColor:
                    status === f.key ? "var(--color-green)" : "var(--color-line)",
                  background: status === f.key ? "var(--color-green)" : "transparent",
                  color: status === f.key ? "#fff" : "var(--color-ink-soft)",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        }
      />

      <Modal
        open={!!open}
        onClose={() => setOpen(null)}
        title={open ? `${open.reference_code} — ${open.full_name}` : ""}
        wide
      >
        {open && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <StatusBadge status={tone(open.status)} label={titleize(open.status)} />
              <span className="text-sm text-[var(--color-ink-faint)]">
                Started {fmtDateTime(open.created_at)}
                {open.submitter_ip ? ` · from ${open.submitter_ip}` : ""}
              </span>
            </div>

            <div>
              <h4 className="mb-3 font-bold">Declared information</h4>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="Full name" value={open.full_name} />
                <Field label="Mobile" value={open.phone} />
                <Field label="Email" value={open.email} />
                <Field label="Date of birth" value={open.date_of_birth} />
                <Field
                  label="Date of joining AAU/AVFU"
                  value={open.date_of_joining_aau_avfu}
                />
                <Field
                  label="Date of joining present post"
                  value={open.date_of_joining_present_post}
                />
                <Field
                  label="Expected date of retirement"
                  value={open.expected_date_of_retirement}
                />
                <Field label="Gender" value={open.gender} />
                <Field label="Blood group" value={open.blood_group} />
                <Field label="Father's name" value={open.father_name} />
                <Field label="Mother's name" value={open.mother_name} />
                <Field label="Marital status" value={open.marital_status} />
                <Field label="Nationality" value={open.nationality} />
                <Field label="Category" value={open.category} />
                <Field label="Aadhaar" value={open.aadhaar_number} mono />
                <Field label="PAN" value={open.pan_number} mono />
                <Field
                  label="Emergency contact"
                  value={
                    open.emergency_contact_name
                      ? `${open.emergency_contact_name} · ${open.emergency_contact_phone}`
                      : ""
                  }
                />
                <Field label="Bank" value={open.bank_name} />
                <Field label="Account no." value={open.bank_account_number} mono />
                <Field label="IFSC" value={open.bank_ifsc} mono />
                <div className="sm:col-span-3">
                  <Field label="Permanent address" value={open.permanent_address} />
                </div>
                <div className="sm:col-span-3">
                  <Field label="Present address" value={open.present_address} />
                </div>
              </div>
            </div>

            <div>
              <h4 className="mb-3 font-bold">
                Documents ({open.documents.length})
              </h4>
              {open.documents.length === 0 ? (
                <Empty message="No documents attached" />
              ) : (
                <ul className="space-y-2">
                  {open.documents.map((doc) => (
                    <li
                      key={doc.id}
                      className="flex flex-wrap items-center gap-3 rounded-xl border border-[var(--color-line)] p-3"
                    >
                      <FileText size={18} className="text-[var(--color-green)]" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold">{doc.doc_type}</p>
                        <p className="truncate text-xs text-[var(--color-ink-faint)]">
                          {doc.original_filename} · {fmtBytes(doc.size_bytes)} ·{" "}
                          {fmtDateTime(doc.uploaded_at)}
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          downloadFile(
                            `/api/submissions/${open.id}/documents/${doc.id}/file`,
                            doc.original_filename
                          )
                        }
                        className="btn btn-ghost px-3 py-1.5 text-sm"
                      >
                        Open
                      </button>
                      <button
                        onClick={() => verifyDoc(doc, !doc.is_verified)}
                        className="btn btn-ghost px-3 py-1.5 text-sm"
                        style={
                          doc.is_verified
                            ? {
                                background: "var(--color-green-tint)",
                                borderColor: "var(--color-green-soft)",
                              }
                            : undefined
                        }
                      >
                        <BadgeCheck size={16} />
                        {doc.is_verified ? "Checked" : "Mark checked"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {reviewable ? (
              <div className="rounded-xl bg-[var(--color-surface-2)] p-4">
                <h4 className="mb-3 font-bold">Confirm placement and decide</h4>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="label">Office / org unit</label>
                    <OrgUnitSelect
                      value={placement.org_unit_id ? Number(placement.org_unit_id) : null}
                      onChange={(id) =>
                        setPlacement({ ...placement, org_unit_id: id ? String(id) : "" })
                      }
                      placeholder="Not assigned"
                    />
                  </div>
                  <div>
                    <label className="label">Designation</label>
                    <select
                      className="input"
                      value={placement.designation_id}
                      onChange={(e) =>
                        setPlacement({ ...placement, designation_id: e.target.value })
                      }
                    >
                      <option value="">Not assigned</option>
                      {(designations ?? []).map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label">Campus</label>
                    <select
                      className="input"
                      value={placement.location_id}
                      onChange={(e) =>
                        setPlacement({ ...placement, location_id: e.target.value })
                      }
                    >
                      <option value="">Not assigned</option>
                      {(locations ?? []).map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label">Reporting authority</label>
                    <select
                      className="input"
                      value={placement.reports_to_id}
                      onChange={(e) =>
                        setPlacement({ ...placement, reports_to_id: e.target.value })
                      }
                    >
                      <option value="">Set later</option>
                      {(employees ?? []).map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.full_name}
                          {e.designation ? ` — ${e.designation}` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <label className="label mt-4">Verification remark</label>
                <textarea
                  className="input min-h-20"
                  value={remark}
                  onChange={(e) => setRemark(e.target.value)}
                  placeholder="Required when rejecting or requesting a correction"
                />

                <div className="mt-3 flex flex-wrap gap-2">
                  {open.status === "submitted" && (
                    <button
                      onClick={() => act("start-review", "Marked under review")}
                      className="btn btn-ghost"
                      disabled={busy}
                    >
                      Start review
                    </button>
                  )}
                  <button
                    onClick={approve}
                    className="btn btn-primary"
                    disabled={busy}
                  >
                    {busy ? (
                      <Spinner />
                    ) : (
                      <>
                        <UserPlus size={18} /> Approve and admit to HRMS
                      </>
                    )}
                  </button>
                  <button
                    onClick={() =>
                      act("request-resubmission", "Correction requested")
                    }
                    className="btn btn-ghost"
                    disabled={busy}
                  >
                    <RotateCcw size={18} /> Request correction
                  </button>
                  <button
                    onClick={() => act("reject", "Submission rejected")}
                    className="btn btn-danger"
                    disabled={busy}
                  >
                    <XCircle size={18} /> Reject
                  </button>
                </div>
              </div>
            ) : (
              <div className="rounded-xl bg-[var(--color-surface-2)] p-4 text-sm text-[var(--color-ink-soft)]">
                {open.status === "approved" && open.hrms_employee_id ? (
                  <p className="flex items-center gap-2 text-[var(--color-green)]">
                    <CheckCircle2 size={18} />
                    Admitted as{" "}
                    <span className="font-mono font-bold">
                      {open.hrms_employee_id}
                    </span>
                  </p>
                ) : (
                  <p>
                    This submission is <strong>{titleize(open.status)}</strong>.
                  </p>
                )}
                {open.reviewed_by_name && (
                  <p className="mt-1">
                    Last acted on by {open.reviewed_by_name} on{" "}
                    {fmtDateTime(open.reviewed_at)}.
                  </p>
                )}
                {open.reviewer_remark && (
                  <p className="mt-1">Remark: {open.reviewer_remark}</p>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </>
  );
}
