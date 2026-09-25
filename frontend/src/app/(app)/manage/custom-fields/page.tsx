"use client";

import { useState } from "react";
import { FileText, Plus, Power, SlidersHorizontal } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { OrgUnitSelect } from "@/components/OrgUnitSelect";
import { titleize } from "@/lib/format";
import { SectionTitle, Spinner, StatusBadge } from "@/components/ui";

interface CustomField {
  id: number;
  key: string;
  label: string;
  field_type: string;
  options: string[];
  is_required: boolean;
  org_unit_id: number | null;
  org_unit_name: string | null;
  help_text: string;
  is_active: boolean;
}

interface DocRequirement {
  id: number;
  label: string;
  org_unit_id: number | null;
  org_unit_name: string | null;
  is_required: boolean;
  is_active: boolean;
}

const FIELD_TYPES = ["text", "number", "date", "boolean", "select"];

const BLANK_FIELD = {
  key: "",
  label: "",
  field_type: "text",
  options: "",
  is_required: false,
  org_unit_id: "",
  help_text: "",
};

const BLANK_DOC = { label: "", org_unit_id: "", is_required: true };

export default function CustomFieldsPage() {
  const { push } = useToast();
  const [tab, setTab] = useState<"fields" | "documents">("fields");

  const { data: fields, loading: fieldsLoading, reload: reloadFields } =
    useApi<CustomField[]>("/api/custom-fields");
  const { data: docs, loading: docsLoading, reload: reloadDocs } =
    useApi<DocRequirement[]>("/api/custom-documents");

  const [fieldOpen, setFieldOpen] = useState(false);
  const [fieldForm, setFieldForm] = useState({ ...BLANK_FIELD });
  const [docOpen, setDocOpen] = useState(false);
  const [docForm, setDocForm] = useState({ ...BLANK_DOC });
  const [busy, setBusy] = useState(false);

  async function createField() {
    setBusy(true);
    try {
      await api.post("/api/custom-fields", {
        key: fieldForm.key,
        label: fieldForm.label,
        field_type: fieldForm.field_type,
        options: fieldForm.options
          ? fieldForm.options.split(",").map((o) => o.trim()).filter(Boolean)
          : [],
        is_required: fieldForm.is_required,
        org_unit_id: fieldForm.org_unit_id
          ? Number(fieldForm.org_unit_id)
          : null,
        help_text: fieldForm.help_text,
      });
      push("success", "Custom field created");
      setFieldOpen(false);
      setFieldForm({ ...BLANK_FIELD });
      reloadFields();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not create field");
    } finally {
      setBusy(false);
    }
  }

  async function toggleField(row: CustomField) {
    try {
      if (row.is_active) {
        await api.del(`/api/custom-fields/${row.id}`);
      } else {
        await api.put(`/api/custom-fields/${row.id}`, { is_active: true });
      }
      reloadFields();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  async function createDoc() {
    setBusy(true);
    try {
      await api.post("/api/custom-documents", {
        label: docForm.label,
        org_unit_id: docForm.org_unit_id ? Number(docForm.org_unit_id) : null,
        is_required: docForm.is_required,
      });
      push("success", "Document requirement added");
      setDocOpen(false);
      setDocForm({ ...BLANK_DOC });
      reloadDocs();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not create requirement");
    } finally {
      setBusy(false);
    }
  }

  async function toggleDoc(row: DocRequirement) {
    try {
      if (row.is_active) {
        await api.del(`/api/custom-documents/${row.id}`);
      } else {
        await api.put(`/api/custom-documents/${row.id}`, { is_active: true });
      }
      reloadDocs();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  const fieldColumns: Column<CustomField>[] = [
    {
      header: "Field",
      value: (r) => `${r.label} ${r.key}`,
      cell: (r) => (
        <div>
          <p className="font-semibold">{r.label}</p>
          <p className="font-mono text-xs text-[var(--color-ink-faint)]">{r.key}</p>
        </div>
      ),
    },
    { header: "Type", value: (r) => r.field_type, cell: (r) => titleize(r.field_type) },
    {
      header: "Applies to",
      value: (r) => r.org_unit_name ?? "University-wide",
      cell: (r) => r.org_unit_name ?? "University-wide",
    },
    {
      header: "Required",
      value: (r) => (r.is_required ? "Yes" : "No"),
      cell: (r) => (r.is_required ? "Yes" : "No"),
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
      header: "",
      cell: (r) => (
        <button
          onClick={() => toggleField(r)}
          className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-2)]"
          title={r.is_active ? "Deactivate" : "Reactivate"}
        >
          <Power size={15} /> <span>{r.is_active ? "Deactivate" : "Reactivate"}</span>
        </button>
      ),
    },
  ];

  const docColumns: Column<DocRequirement>[] = [
    { header: "Document type", value: (r) => r.label, cell: (r) => r.label },
    {
      header: "Applies to",
      value: (r) => r.org_unit_name ?? "University-wide",
      cell: (r) => r.org_unit_name ?? "University-wide",
    },
    {
      header: "Required",
      value: (r) => (r.is_required ? "Yes" : "No"),
      cell: (r) => (r.is_required ? "Yes" : "No"),
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
      header: "",
      cell: (r) => (
        <button
          onClick={() => toggleDoc(r)}
          className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-ink-soft)] hover:bg-[var(--color-surface-2)]"
          title={r.is_active ? "Deactivate" : "Reactivate"}
        >
          <Power size={15} /> <span>{r.is_active ? "Deactivate" : "Reactivate"}</span>
        </button>
      ),
    },
  ];

  return (
    <>
      <SectionTitle
        title="Custom Fields"
        subtitle="Add employee data fields or required document types without any code change. Optionally scope one to a single department — required fields/documents can differ by department."
      />

      <div className="mb-5 flex gap-2">
        {(["fields", "documents"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="rounded-full border px-4 py-2 text-sm font-semibold transition-colors"
            style={{
              borderColor: tab === t ? "var(--color-green)" : "var(--color-line)",
              background: tab === t ? "var(--color-green)" : "transparent",
              color: tab === t ? "#fff" : "var(--color-ink-soft)",
            }}
          >
            {t === "fields" ? (
              <>
                <SlidersHorizontal size={15} className="mr-1.5 inline" /> Employee
                Fields
              </>
            ) : (
              <>
                <FileText size={15} className="mr-1.5 inline" /> Document
                Requirements
              </>
            )}
          </button>
        ))}
      </div>

      {tab === "fields" ? (
        <>
          <div className="mb-4 flex justify-end">
            <button onClick={() => setFieldOpen(true)} className="btn btn-primary">
              <Plus size={18} /> Add field
            </button>
          </div>
          <DataTable
            columns={fieldColumns}
            rows={fields ?? []}
            loading={fieldsLoading}
            empty="No custom fields defined yet"
            searchPlaceholder="Search fields"
          />
        </>
      ) : (
        <>
          <div className="mb-4 flex justify-end">
            <button onClick={() => setDocOpen(true)} className="btn btn-primary">
              <Plus size={18} /> Add document type
            </button>
          </div>
          <DataTable
            columns={docColumns}
            rows={docs ?? []}
            loading={docsLoading}
            empty="No custom document requirements defined yet"
            searchPlaceholder="Search document types"
          />
        </>
      )}

      <Modal open={fieldOpen} onClose={() => setFieldOpen(false)} title="Add employee field">
        <div className="space-y-4">
          <div>
            <label className="label">Field key (unique, no spaces) *</label>
            <input
              className="input font-mono"
              value={fieldForm.key}
              onChange={(e) =>
                setFieldForm({ ...fieldForm, key: e.target.value.replace(/\s+/g, "_") })
              }
              placeholder="e.g. blood_donor_id"
            />
          </div>
          <div>
            <label className="label">Label shown on the form *</label>
            <input
              className="input"
              value={fieldForm.label}
              onChange={(e) => setFieldForm({ ...fieldForm, label: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Field type</label>
            <select
              className="input"
              value={fieldForm.field_type}
              onChange={(e) => setFieldForm({ ...fieldForm, field_type: e.target.value })}
            >
              {FIELD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {titleize(t)}
                </option>
              ))}
            </select>
          </div>
          {fieldForm.field_type === "select" && (
            <div>
              <label className="label">Options (comma-separated)</label>
              <input
                className="input"
                value={fieldForm.options}
                onChange={(e) => setFieldForm({ ...fieldForm, options: e.target.value })}
                placeholder="Option A, Option B, Option C"
              />
            </div>
          )}
          <div>
            <label className="label">Applies to (leave blank for university-wide)</label>
            <OrgUnitSelect
              value={fieldForm.org_unit_id ? Number(fieldForm.org_unit_id) : null}
              onChange={(id) =>
                setFieldForm({ ...fieldForm, org_unit_id: id ? String(id) : "" })
              }
              placeholder="University-wide"
            />
          </div>
          <div>
            <label className="label">Help text (optional)</label>
            <input
              className="input"
              value={fieldForm.help_text}
              onChange={(e) => setFieldForm({ ...fieldForm, help_text: e.target.value })}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
            <input
              type="checkbox"
              checked={fieldForm.is_required}
              onChange={(e) =>
                setFieldForm({ ...fieldForm, is_required: e.target.checked })
              }
            />
            Required
          </label>
        </div>
        <button
          onClick={createField}
          className="btn btn-primary mt-4 w-full"
          disabled={busy || !fieldForm.key || !fieldForm.label}
        >
          {busy ? <Spinner /> : "Create field"}
        </button>
      </Modal>

      <Modal open={docOpen} onClose={() => setDocOpen(false)} title="Add required document type">
        <div className="space-y-4">
          <div>
            <label className="label">Document type name *</label>
            <input
              className="input"
              value={docForm.label}
              onChange={(e) => setDocForm({ ...docForm, label: e.target.value })}
              placeholder="e.g. No Objection Certificate"
            />
          </div>
          <div>
            <label className="label">Applies to (leave blank for university-wide)</label>
            <OrgUnitSelect
              value={docForm.org_unit_id ? Number(docForm.org_unit_id) : null}
              onChange={(id) => setDocForm({ ...docForm, org_unit_id: id ? String(id) : "" })}
              placeholder="University-wide"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
            <input
              type="checkbox"
              checked={docForm.is_required}
              onChange={(e) => setDocForm({ ...docForm, is_required: e.target.checked })}
            />
            Required
          </label>
        </div>
        <button
          onClick={createDoc}
          className="btn btn-primary mt-4 w-full"
          disabled={busy || !docForm.label}
        >
          {busy ? <Spinner /> : "Add document type"}
        </button>
      </Modal>
    </>
  );
}
