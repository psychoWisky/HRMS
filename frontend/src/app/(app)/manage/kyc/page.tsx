"use client";

import { useMemo, useState } from "react";
import {
  BadgeCheck,
  CheckCircle2,
  Eye,
  FileText,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { ApiError, api, downloadFile } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { KYC_LABEL, fmtBytes, fmtDateTime, kycTone } from "@/lib/format";
import {
  Empty,
  Field,
  SectionTitle,
  Spinner,
  StatusBadge,
} from "@/components/ui";

interface KYCDocument {
  id: number;
  doc_type: string;
  original_filename: string;
  size_bytes: number;
  is_verified: boolean;
  verifier_remark: string;
  uploaded_at: string;
}

interface KYCHistory {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  actor_name: string;
  remark: string;
  created_at: string;
}

interface KYCRecord {
  id: number;
  employee_id: number;
  employee_name: string;
  hrms_employee_id: string;
  organization: string | null;
  designation: string | null;
  status: string;
  father_name: string;
  mother_name: string;
  date_of_birth: string | null;
  gender: string;
  blood_group: string;
  marital_status: string;
  nationality: string;
  category: string;
  aadhaar_number: string;
  pan_number: string;
  personal_email: string;
  contact_phone: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  permanent_address: string;
  present_address: string;
  bank_name: string;
  bank_account_number: string;
  bank_ifsc: string;
  submitted_at: string | null;
  verified_at: string | null;
  verified_by_name: string | null;
  verifier_remark: string;
  documents: KYCDocument[];
  history: KYCHistory[];
}

const FILTERS = [
  { key: "", label: "All" },
  { key: "submitted", label: "Submitted" },
  { key: "under_verification", label: "Under verification" },
  { key: "resubmission_required", label: "Resubmission required" },
  { key: "verified", label: "Verified" },
  { key: "rejected", label: "Rejected" },
  { key: "not_started", label: "Not started" },
];

export default function EmployeeDocumentsPage() {
  const [status, setStatus] = useState("");

  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "1000" });
    if (status) params.set("kyc_status", status);
    return `/api/kyc?${params.toString()}`;
  }, [status]);

  const { data, loading, reload } = useApi<KYCRecord[]>(path);
  const { push } = useToast();

  const [open, setOpen] = useState<KYCRecord | null>(null);
  const [remark, setRemark] = useState("");
  const [busy, setBusy] = useState(false);

  async function act(action: string, label: string) {
    if (!open) return;
    setBusy(true);
    try {
      const updated = await api.post<KYCRecord>(
        `/api/kyc/${open.id}/${action}`,
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

  async function verifyDoc(doc: KYCDocument, verified: boolean) {
    if (!open) return;
    try {
      await api.post(`/api/kyc/${open.id}/documents/${doc.id}/verify`, {
        is_verified: verified,
        remark: "",
      });
      const refreshed = await api.get<KYCRecord>(`/api/kyc/${open.id}`);
      setOpen(refreshed);
      push("success", verified ? "Document marked verified" : "Mark removed");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  const columns: Column<KYCRecord>[] = [
    {
      header: "Employee",
      value: (r) => `${r.employee_name} ${r.hrms_employee_id}`,
      cell: (r) => (
        <div>
          <p className="font-semibold">{r.employee_name}</p>
          <p className="font-mono text-xs text-[var(--color-ink-faint)]">
            {r.hrms_employee_id}
          </p>
        </div>
      ),
    },
    {
      header: "Designation",
      value: (r) => r.designation ?? "",
      cell: (r) => r.designation ?? "—",
    },
    {
      header: "Organisation",
      value: (r) => r.organization ?? "",
      cell: (r) => <span className="text-sm">{r.organization ?? "—"}</span>,
    },
    {
      header: "Documents",
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
      value: (r) => KYC_LABEL[r.status] ?? r.status,
      cell: (r) => (
        <StatusBadge
          status={kycTone(r.status)}
          label={KYC_LABEL[r.status] ?? r.status}
        />
      ),
    },
    {
      header: "",
      cell: (r) => (
        <button
          onClick={() => {
            setOpen(r);
            setRemark("");
          }}
          className="btn btn-ghost px-3 py-1.5 text-sm"
        >
          <Eye size={16} /> Review
        </button>
      ),
    },
  ];

  const reviewable =
    open && ["submitted", "under_verification"].includes(open.status);

  return (
    <>
      <SectionTitle
        title="Employee Documents"
        subtitle="Document records of employees already on the HRMS. Every check is manual — nothing is verified automatically. New joiners arrive through New Submissions."
      />

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No document records in this state"
        searchPlaceholder="Search employee, HRMS ID, office or status"
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
                  background:
                    status === f.key ? "var(--color-green)" : "transparent",
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
        title={open ? `KYC — ${open.employee_name}` : ""}
        wide
      >
        {open && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <StatusBadge
                status={kycTone(open.status)}
                label={KYC_LABEL[open.status] ?? open.status}
              />
              <span className="font-mono text-sm text-[var(--color-ink-faint)]">
                {open.hrms_employee_id}
              </span>
            </div>

            <div>
              <h4 className="mb-3 font-bold">Declared information</h4>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="Father's Name" value={open.father_name} />
                <Field label="Mother's Name" value={open.mother_name} />
                <Field label="Date of Birth" value={open.date_of_birth} />
                <Field label="Gender" value={open.gender} />
                <Field label="Blood Group" value={open.blood_group} />
                <Field label="Marital Status" value={open.marital_status} />
                <Field label="Nationality" value={open.nationality} />
                <Field label="Category" value={open.category} />
                <Field label="Aadhaar" value={open.aadhaar_number} mono />
                <Field label="PAN" value={open.pan_number} mono />
                <Field label="Personal Email" value={open.personal_email} />
                <Field label="Contact Phone" value={open.contact_phone} />
                <Field
                  label="Emergency Contact"
                  value={
                    open.emergency_contact_name
                      ? `${open.emergency_contact_name} · ${open.emergency_contact_phone}`
                      : ""
                  }
                />
                <Field label="Bank" value={open.bank_name} />
                <Field label="Account No." value={open.bank_account_number} mono />
                <Field label="IFSC" value={open.bank_ifsc} mono />
                <div className="sm:col-span-3">
                  <Field label="Permanent Address" value={open.permanent_address} />
                </div>
                <div className="sm:col-span-3">
                  <Field label="Present Address" value={open.present_address} />
                </div>
              </div>
            </div>

            <div>
              <h4 className="mb-3 font-bold">
                Documents ({open.documents.length})
              </h4>
              {open.documents.length === 0 ? (
                <Empty message="No documents were uploaded" />
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
                            `/api/kyc/${open.id}/documents/${doc.id}/file`,
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
                        {doc.is_verified ? "Verified" : "Mark checked"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {reviewable ? (
              <div className="rounded-xl bg-[var(--color-surface-2)] p-4">
                <label className="label">Verification remark</label>
                <textarea
                  className="input min-h-20"
                  value={remark}
                  onChange={(e) => setRemark(e.target.value)}
                  placeholder="Required when rejecting or requesting a resubmission"
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  {open.status === "submitted" && (
                    <button
                      onClick={() => act("start-verification", "Marked under verification")}
                      className="btn btn-ghost"
                      disabled={busy}
                    >
                      Start verification
                    </button>
                  )}
                  <button
                    onClick={() => act("approve", "KYC approved")}
                    className="btn btn-primary"
                    disabled={busy}
                  >
                    {busy ? <Spinner /> : <><CheckCircle2 size={18} /> Approve</>}
                  </button>
                  <button
                    onClick={() =>
                      act("request-resubmission", "Resubmission requested")
                    }
                    className="btn btn-ghost"
                    disabled={busy}
                  >
                    <RotateCcw size={18} /> Request resubmission
                  </button>
                  <button
                    onClick={() => act("reject", "KYC rejected")}
                    className="btn btn-danger"
                    disabled={busy}
                  >
                    <XCircle size={18} /> Reject
                  </button>
                </div>
              </div>
            ) : (
              <p className="rounded-xl bg-[var(--color-surface-2)] p-4 text-sm text-[var(--color-ink-soft)]">
                This record is <strong>{KYC_LABEL[open.status] ?? open.status}</strong>
                {open.verified_by_name
                  ? ` — last acted on by ${open.verified_by_name} on ${fmtDateTime(
                      open.verified_at
                    )}.`
                  : "."}
                {open.verifier_remark && ` Remark: ${open.verifier_remark}`}
              </p>
            )}

            <div>
              <h4 className="mb-3 font-bold">Verification history</h4>
              {open.history.length === 0 ? (
                <p className="text-sm text-[var(--color-ink-faint)]">
                  No activity recorded.
                </p>
              ) : (
                <ol className="space-y-2">
                  {open.history.map((h) => (
                    <li
                      key={h.id}
                      className="border-l-2 border-[var(--color-line)] pl-3 text-sm"
                    >
                      <p>
                        <strong>{KYC_LABEL[h.from_status] ?? h.from_status}</strong>
                        {" → "}
                        <strong>{KYC_LABEL[h.to_status] ?? h.to_status}</strong>
                      </p>
                      <p className="text-xs text-[var(--color-ink-faint)]">
                        {fmtDateTime(h.created_at)} · {h.actor_name}
                      </p>
                      {h.remark && (
                        <p className="text-[var(--color-ink-soft)]">{h.remark}</p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
