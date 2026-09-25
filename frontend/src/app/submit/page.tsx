"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  FileText,
  Info,
  KeyRound,
  Send,
  ShieldCheck,
  Trash2,
  Upload,
} from "lucide-react";
import { ApiError, publicApi } from "@/lib/api";
import { Logo } from "@/components/Logo";
import { useToast } from "@/components/Toast";
import { Empty, Spinner } from "@/components/ui";
import { fmtBytes, fmtDateTime } from "@/lib/format";

const STORAGE_KEY = "avfu_submission";

interface Option {
  id: number;
  name: string;
  group: string;
}

interface SubmissionDoc {
  id: number;
  doc_type: string;
  original_filename: string;
  size_bytes: number;
  uploaded_at: string;
}

interface Submission {
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
  reviewer_remark: string;
  documents: SubmissionDoc[];
  can_edit: boolean;
  hrms_employee_id: string | null;
}

const STATUS_TONE: Record<string, { bg: string; fg: string; label: string }> = {
  draft: { bg: "#eef2f0", fg: "#41504a", label: "Draft — not yet sent" },
  submitted: { bg: "#fdf6e3", fg: "#6b5510", label: "Submitted — awaiting review" },
  under_review: { bg: "#fdf6e3", fg: "#6b5510", label: "Under review by HR" },
  resubmission_required: {
    bg: "#fdf6e3",
    fg: "#6b5510",
    label: "Correction required",
  },
  approved: { bg: "#e6efe9", fg: "#14532d", label: "Approved — admitted to AVFU HRMS" },
  rejected: { bg: "#fbf0f0", fg: "#8a1c1c", label: "Rejected" },
};

const BLANK = {
  full_name: "",
  email: "",
  phone: "",
  gender: "",
  date_of_birth: "",
  date_of_joining_aau_avfu: "",
  date_of_joining_present_post: "",
  org_unit_id: "",
  designation_id: "",
  location_id: "",
  date_of_joining: "",
  father_name: "",
  mother_name: "",
  blood_group: "",
  marital_status: "",
  nationality: "Indian",
  category: "",
  aadhaar_number: "",
  pan_number: "",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  permanent_address: "",
  present_address: "",
  bank_name: "",
  bank_account_number: "",
  bank_ifsc: "",
};

type Form = typeof BLANK;

const PERSONAL: [keyof Form, string, string?, boolean?][] = [
  ["full_name", "Full name", "text", true],
  ["phone", "Mobile number", "tel", true],
  ["email", "Email address", "email"],
  ["date_of_birth", "Date of birth (attach proof)", "date", true],
  [
    "date_of_joining_aau_avfu",
    "Date of joining AAU/AVFU (attach proof)",
    "date",
  ],
  [
    "date_of_joining_present_post",
    "Date of joining present post (attach proof)",
    "date",
  ],
  ["gender", "Gender"],
  ["blood_group", "Blood group"],
  ["marital_status", "Marital status"],
  ["nationality", "Nationality"],
  ["category", "Category"],
  ["father_name", "Father's name", "text", true],
  ["mother_name", "Mother's name"],
  ["aadhaar_number", "Aadhaar number", "text", true],
  ["pan_number", "PAN number"],
  ["emergency_contact_name", "Emergency contact name"],
  ["emergency_contact_phone", "Emergency contact phone"],
  ["bank_name", "Bank name"],
  ["bank_account_number", "Bank account number"],
  ["bank_ifsc", "Bank IFSC"],
];

function Banner({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? STATUS_TONE.draft;
  return (
    <span
      className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-semibold"
      style={{ background: tone.bg, color: tone.fg }}
    >
      <span className="h-2 w-2 rounded-full bg-current" />
      {tone.label}
    </span>
  );
}

export default function PublicSubmitPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-[var(--color-green)]">
          <Spinner size={30} />
        </div>
      }
    >
      <SubmitPageContent />
    </Suspense>
  );
}

function SubmitPageContent() {
  const { push } = useToast();
  const searchParams = useSearchParams();

  const [form, setForm] = useState<Form>({ ...BLANK });
  const [record, setRecord] = useState<Submission | null>(null);
  const [busy, setBusy] = useState(false);
  const [booting, setBooting] = useState(true);

  const [orgs, setOrgs] = useState<Option[]>([]);
  const [designations, setDesignations] = useState<Option[]>([]);
  const [locations, setLocations] = useState<Option[]>([]);
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [docType, setDocType] = useState("Aadhaar Card");
  const fileRef = useRef<HTMLInputElement>(null);

  // Return to an existing submission by its reference code.
  const [entryRef, setEntryRef] = useState("");

  const load = useCallback(
    async (reference: string, quiet = false) => {
      try {
        const data = await publicApi.get<Submission>(
          `/api/public/submissions/${encodeURIComponent(reference)}`
        );
        setRecord(data);
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ reference: data.reference_code })
        );
        return true;
      } catch (err) {
        if (!quiet) {
          push("error", err instanceof ApiError ? err.message : "Could not load");
        }
        return false;
      }
    },
    [push]
  );

  useEffect(() => {
    (async () => {
      try {
        const [o, d, l, t] = await Promise.all([
          publicApi.get<Option[]>("/api/public/org-units"),
          publicApi.get<Option[]>("/api/public/designations"),
          publicApi.get<Option[]>("/api/public/locations"),
          publicApi.get<string[]>("/api/public/document-types"),
        ]);
        setOrgs(o);
        setDesignations(d);
        setLocations(l);
        setDocTypes(t);
        if (t.length) setDocType(t[0]);
      } catch {
        push("error", "Could not reach the AVFU HRMS server");
      }

      // A shared link may carry the reference code directly.
      const linkRef = searchParams.get("ref");
      if (linkRef) {
        const ok = await load(linkRef, true);
        if (ok) {
          setBooting(false);
          return;
        }
      }

      // Otherwise resume whatever was last opened on this browser.
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        try {
          const { reference } = JSON.parse(saved);
          if (reference) await load(reference, true);
        } catch {
          localStorage.removeItem(STORAGE_KEY);
        }
      }
      setBooting(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function set<K extends keyof Form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function payload() {
    const out: Record<string, unknown> = { ...form };
    for (const key of ["org_unit_id", "designation_id", "location_id"]) {
      out[key] = form[key as keyof Form] ? Number(form[key as keyof Form]) : null;
    }
    for (const key of [
      "date_of_birth",
      "date_of_joining_aau_avfu",
      "date_of_joining_present_post",
      "date_of_joining",
    ]) {
      out[key] = form[key as keyof Form] || null;
    }
    return out;
  }

  async function startNew() {
    setBusy(true);
    try {
      const created = await publicApi.post<{ reference_code: string }>(
        "/api/public/submissions"
      );
      await load(created.reference_code);
      push("success", `Submission started — reference ${created.reference_code}`);
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not start");
    } finally {
      setBusy(false);
    }
  }

  async function openExisting() {
    if (!entryRef.trim()) {
      push("error", "Enter your reference code");
      return;
    }
    setBusy(true);
    const ok = await load(entryRef.trim());
    setBusy(false);
    if (ok) push("success", "Submission found");
  }

  async function saveChanges() {
    if (!record) return;
    setBusy(true);
    try {
      await publicApi.put(
        `/api/public/submissions/${record.reference_code}`,
        payload()
      );
      await load(record.reference_code);
      push("success", "Details saved");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument() {
    const file = fileRef.current?.files?.[0];
    if (!record || !file) {
      push("error", "Choose a file first");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("doc_type", docType);
      fd.append("file", file);
      await publicApi.upload(
        `/api/public/submissions/${record.reference_code}/documents`,
        fd
      );
      if (fileRef.current) fileRef.current.value = "";
      await load(record.reference_code);
      push("success", `${file.name} attached`);
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function removeDocument(id: number) {
    if (!record) return;
    setBusy(true);
    try {
      await publicApi.del(
        `/api/public/submissions/${record.reference_code}/documents/${id}`
      );
      await load(record.reference_code);
      push("success", "Document removed");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function finalise() {
    if (!record) return;
    setBusy(true);
    try {
      await publicApi.post(
        `/api/public/submissions/${record.reference_code}/submit`
      );
      await load(record.reference_code);
      push("success", "Submitted to AVFU HR for verification");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Submission failed");
    } finally {
      setBusy(false);
    }
  }

  function startOver() {
    localStorage.removeItem(STORAGE_KEY);
    setRecord(null);
    setForm({ ...BLANK });
    setEntryRef("");
  }

  // Prefill the editable form whenever the record changes.
  useEffect(() => {
    if (!record) return;
    setForm({
      full_name: record.full_name ?? "",
      email: record.email ?? "",
      phone: record.phone ?? "",
      gender: record.gender ?? "",
      date_of_birth: record.date_of_birth ?? "",
      date_of_joining_aau_avfu: record.date_of_joining_aau_avfu ?? "",
      date_of_joining_present_post: record.date_of_joining_present_post ?? "",
      org_unit_id: String(record.org_unit_id ?? ""),
      designation_id: String(record.designation_id ?? ""),
      location_id: String(record.location_id ?? ""),
      date_of_joining: record.date_of_joining ?? "",
      father_name: record.father_name ?? "",
      mother_name: record.mother_name ?? "",
      blood_group: record.blood_group ?? "",
      marital_status: record.marital_status ?? "",
      nationality: record.nationality ?? "Indian",
      category: record.category ?? "",
      aadhaar_number: record.aadhaar_number ?? "",
      pan_number: record.pan_number ?? "",
      emergency_contact_name: record.emergency_contact_name ?? "",
      emergency_contact_phone: record.emergency_contact_phone ?? "",
      permanent_address: record.permanent_address ?? "",
      present_address: record.present_address ?? "",
      bank_name: record.bank_name ?? "",
      bank_account_number: record.bank_account_number ?? "",
      bank_ifsc: record.bank_ifsc ?? "",
    });
  }, [record]);

  const placement = (
    <div className="grid gap-4 sm:grid-cols-3">
      <div>
        <label className="label">Office you are joining</label>
        <select
          className="input"
          value={form.org_unit_id}
          onChange={(e) => set("org_unit_id", e.target.value)}
        >
          <option value="">Select…</option>
          {orgs.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Designation</label>
        <select
          className="input"
          value={form.designation_id}
          onChange={(e) => set("designation_id", e.target.value)}
        >
          <option value="">Select…</option>
          {designations.map((d) => (
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
          value={form.location_id}
          onChange={(e) => set("location_id", e.target.value)}
        >
          <option value="">Select…</option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );

  const fields = (
    <>
      <div className="grid gap-4 sm:grid-cols-3">
        {PERSONAL.map(([key, label, type, required]) => (
          <div key={key}>
            <label className="label">
              {label}
              {required && <span style={{ color: "var(--color-danger)" }}> *</span>}
            </label>
            <input
              className="input"
              type={type ?? "text"}
              value={form[key]}
              onChange={(e) => set(key, e.target.value)}
            />
          </div>
        ))}
        <div>
          <label className="label">Date of joining (if known)</label>
          <input
            className="input"
            type="date"
            value={form.date_of_joining}
            onChange={(e) => set("date_of_joining", e.target.value)}
          />
        </div>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label">
            Permanent address<span style={{ color: "var(--color-danger)" }}> *</span>
          </label>
          <textarea
            className="input min-h-24"
            value={form.permanent_address}
            onChange={(e) => set("permanent_address", e.target.value)}
          />
        </div>
        <div>
          <label className="label">Present address</label>
          <textarea
            className="input min-h-24"
            value={form.present_address}
            onChange={(e) => set("present_address", e.target.value)}
          />
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      {/* Header */}
      <header
        className="border-b px-5 py-4 sm:px-8"
        style={{ background: "#fff", borderColor: "var(--color-line)" }}
      >
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <Logo size={44} />
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold">New Employee Document Submission</h1>
          <p className="mt-2 max-w-3xl text-[var(--color-ink-soft)]">
            Start a new submission below, then fill in your details and attach
            your documents. You will get a reference code — keep it safe, as it
            is how you return to this submission and track its status.
          </p>
        </div>

        {booting ? (
          <div className="card flex items-center justify-center p-16 text-[var(--color-green)]">
            <Spinner size={30} />
          </div>
        ) : !record ? (
          <div className="card mx-auto max-w-lg p-6">
            <div className="mb-4 flex items-center gap-2 text-[var(--color-green)]">
              <KeyRound size={22} />
              <h2 className="text-xl font-bold text-[var(--color-ink)]">
                Start your submission
              </h2>
            </div>
            <p className="mb-5 text-sm text-[var(--color-ink-faint)]">
              First time here? Start a new submission. Coming back? Enter the
              reference code you were given.
            </p>
            <button
              onClick={startNew}
              className="btn btn-primary w-full"
              disabled={busy}
            >
              {busy ? <Spinner /> : "Start a new submission"}
            </button>

            <div className="my-5 flex items-center gap-3 text-xs text-[var(--color-ink-faint)]">
              <span className="h-px flex-1 bg-[var(--color-line)]" />
              OR
              <span className="h-px flex-1 bg-[var(--color-line)]" />
            </div>

            <div className="space-y-3">
              <div>
                <label className="label">Return with a reference code</label>
                <input
                  className="input"
                  placeholder="AVFU-SUB-000001"
                  value={entryRef}
                  onChange={(e) => setEntryRef(e.target.value)}
                />
              </div>
              <button
                onClick={openExisting}
                className="btn btn-ghost w-full"
                disabled={busy || !entryRef.trim()}
              >
                {busy ? <Spinner /> : "Open my submission"}
              </button>
            </div>
            <p className="mt-5 flex items-start gap-2 rounded-xl bg-[var(--color-surface-2)] p-3 text-xs text-[var(--color-ink-soft)]">
              <Info size={15} className="mt-0.5 shrink-0" />
              Nothing is added to the directory until AVFU HR reviews and
              approves your submission.
            </p>
          </div>
        ) : (
          <>
            {/* Reference card */}
            <div className="card mb-5 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                    Your reference
                  </p>
                  <p className="font-mono text-xl font-bold">
                    {record.reference_code}
                  </p>
                  <div className="mt-2">
                    <Banner status={record.status} />
                  </div>
                </div>
                <button
                  onClick={startOver}
                  className="btn btn-ghost px-4 py-2 text-sm"
                >
                  <ArrowLeft size={16} /> Exit this submission
                </button>
              </div>
            </div>

            {record.reviewer_remark && (
              <div
                className="card mb-5 flex gap-3 border-l-4 p-4"
                style={{
                  borderLeftColor:
                    record.status === "rejected"
                      ? "var(--color-danger)"
                      : "var(--color-warn)",
                }}
              >
                <AlertTriangle
                  size={20}
                  className="mt-0.5 shrink-0"
                  style={{
                    color:
                      record.status === "rejected"
                        ? "var(--color-danger)"
                        : "var(--color-warn)",
                  }}
                />
                <div>
                  <p className="font-semibold">
                    {record.status === "rejected"
                      ? "Reason for rejection"
                      : "Message from AVFU HR"}
                  </p>
                  <p className="mt-1 text-[15px] text-[var(--color-ink-soft)]">
                    {record.reviewer_remark}
                  </p>
                </div>
              </div>
            )}

            {record.status === "approved" && (
              <div
                className="card mb-5 border-l-4 p-5"
                style={{ borderLeftColor: "var(--color-green)" }}
              >
                <div className="flex items-center gap-2 text-[var(--color-green)]">
                  <CheckCircle2 size={22} />
                  <p className="text-lg font-bold">
                    Approved — you are now on the AVFU HRMS
                  </p>
                </div>
                {record.hrms_employee_id && (
                  <p className="mt-3">
                    Your HRMS Employee ID is{" "}
                    <span className="font-mono text-lg font-bold">
                      {record.hrms_employee_id}
                    </span>
                  </p>
                )}
              </div>
            )}

            <div className="grid gap-5 lg:grid-cols-3">
              {/* Details */}
              <div className="card p-6 lg:col-span-2">
                <h2 className="mb-4 text-xl font-bold">Your details</h2>
                {record.can_edit ? (
                  <>
                    {placement}
                    <div className="my-5 h-px bg-[var(--color-line)]" />
                    {fields}
                    <button
                      onClick={saveChanges}
                      className="btn btn-ghost mt-5"
                      disabled={busy}
                    >
                      {busy ? <Spinner /> : "Save details"}
                    </button>
                  </>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {[
                      ["Full name", record.full_name],
                      ["Mobile", record.phone],
                      ["Email", record.email],
                      ["Office", record.org_unit],
                      ["Designation", record.designation],
                      ["Campus", record.location],
                      ["Father's name", record.father_name],
                      ["Aadhaar", record.aadhaar_number],
                      ["Submitted", fmtDateTime(record.submitted_at)],
                      ["Reviewed", fmtDateTime(record.reviewed_at)],
                    ].map(([label, value]) => (
                      <div key={label as string}>
                        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                          {label}
                        </p>
                        <p className="mt-1">{value || "—"}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Documents */}
              <div className="card p-6">
                <h2 className="mb-4 text-xl font-bold">
                  Documents ({record.documents.length})
                </h2>

                {record.can_edit && (
                  <div className="mb-4 space-y-2 rounded-xl bg-[var(--color-surface-2)] p-3">
                    <select
                      className="input"
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                    >
                      {docTypes.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png,.webp"
                      className="input text-sm"
                    />
                    <button
                      onClick={uploadDocument}
                      className="btn btn-primary w-full"
                      disabled={busy}
                    >
                      <Upload size={18} /> Attach document
                    </button>
                    <p className="text-xs text-[var(--color-ink-faint)]">
                      PDF, JPEG, PNG or WebP, up to 10 MB each. Include your
                      qualification/educational certificates, PAN card and
                      Aadhaar card.
                    </p>
                  </div>
                )}

                {record.documents.length === 0 ? (
                  <Empty message="No documents attached yet" />
                ) : (
                  <ul className="space-y-2">
                    {record.documents.map((doc) => (
                      <li
                        key={doc.id}
                        className="flex items-start gap-2 rounded-xl border border-[var(--color-line)] p-3"
                      >
                        <FileText
                          size={18}
                          className="mt-0.5 shrink-0 text-[var(--color-green)]"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold">{doc.doc_type}</p>
                          <p className="truncate text-xs text-[var(--color-ink-faint)]">
                            {doc.original_filename} · {fmtBytes(doc.size_bytes)}
                          </p>
                        </div>
                        {record.can_edit && (
                          <button
                            onClick={() => removeDocument(doc.id)}
                            className="shrink-0 text-[var(--color-danger)]"
                            aria-label="Remove"
                          >
                            <Trash2 size={17} />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                {record.can_edit && (
                  <button
                    onClick={finalise}
                    className="btn btn-primary mt-5 w-full"
                    disabled={busy || record.documents.length === 0}
                  >
                    {busy ? (
                      <Spinner />
                    ) : (
                      <>
                        <Send size={18} /> Send to AVFU HR
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            <p className="mt-5 flex items-center justify-end gap-1.5 text-sm text-[var(--color-ink-faint)]">
              <ShieldCheck size={15} />
              Your documents are stored securely and are visible only to AVFU HR.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
