"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { orgUnitLabel } from "@/lib/format";
import { Field, SectionTitle, Spinner } from "@/components/ui";

interface SectionRow {
  id: number;
  name: string;
  sub_kind: string;
  officer_in_charge_name: string | null;
  headcount_note: string;
  employee_count: number;
}

interface Office {
  id: number;
  kind: string;
  sub_kind: string;
  name: string;
  short_code: string;
  path: string;
  college_name: string | null;
  location_name: string | null;
  head_name: string | null;
  reporting_authority_text: string;
  hrms_contact_name: string;
  hrms_contact_designation: string;
  hrms_contact_phone: string;
  hrms_contact_email: string;
  office_email: string;
  employee_count: number;
  part_c: SectionRow[];
}

const SECTION_BLANK = {
  name: "",
  sub_kind: "section",
  officer_in_charge_employee_id: "",
  headcount_note: "",
};

export default function OfficePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { can } = useAuth();
  const { push } = useToast();
  const { data, loading, reload } = useApi<Office>(`/api/org-units/${id}`);

  const canPartC = can(P.orgCreate) || can(P.orgEdit);

  const [secOpen, setSecOpen] = useState(false);
  const [secForm, setSecForm] = useState({ ...SECTION_BLANK });
  const [busy, setBusy] = useState(false);

  if (loading || !data) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size={28} />
      </div>
    );
  }
  const office = data;

  async function saveSection() {
    setBusy(true);
    try {
      await api.post("/api/org-units", {
        kind: "section",
        sub_kind: secForm.sub_kind,
        parent_id: office.id,
        name: secForm.name.trim(),
        headcount_note: secForm.headcount_note,
        officer_in_charge_employee_id: secForm.officer_in_charge_employee_id
          ? Number(secForm.officer_in_charge_employee_id)
          : null,
      });
      push("success", "Section added");
      setSecOpen(false);
      setSecForm({ ...SECTION_BLANK });
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  async function deleteSection(s: SectionRow) {
    try {
      await api.del(`/api/org-units/${s.id}`);
      push("success", `${s.name} deactivated`);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Delete failed");
    }
  }

  return (
    <>
      <Link
        href="/manage/org-units"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-[var(--color-ink-soft)] hover:underline"
      >
        <ArrowLeft size={15} /> Organisation Structure
      </Link>

      <SectionTitle
        title={office.name}
        subtitle={`${orgUnitLabel(office.kind, office.sub_kind)} · ${office.path}`}
      />

      {/* Part A */}
      <div className="card mb-6 p-5">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-[var(--color-ink-muted)]">
          General Information
        </h2>
        <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
          <Field label="Name of the office" value={office.name} />
          <Field label="Short code" value={office.short_code} mono />
          <Field label="College / University" value={office.college_name} />
          <Field label="Campus" value={office.location_name} />
          <Field label="Head of Office" value={office.head_name} />
          <Field
            label="Reporting authority"
            value={office.reporting_authority_text}
          />
          <Field label="HRMS contact" value={office.hrms_contact_name} />
          <Field
            label="Contact designation"
            value={office.hrms_contact_designation}
          />
          <Field label="Contact phone" value={office.hrms_contact_phone} />
          <Field label="Contact email" value={office.hrms_contact_email} />
          <Field label="Office email" value={office.office_email} />
          <Field label="Employees" value={String(office.employee_count)} />
        </div>
      </div>

      {/* Sections / Units / Cells */}
      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wide text-[var(--color-ink-muted)]">
            Sections / Units / Cells
          </h2>
          {canPartC && (
            <button
              onClick={() => setSecOpen(true)}
              className="btn btn-primary px-3 py-1.5 text-sm"
            >
              <Plus size={15} /> Add section
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-line)] text-left text-xs uppercase text-[var(--color-ink-faint)]">
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Officer-in-charge</th>
                <th className="py-2 pr-3 text-right">Employees</th>
                {canPartC && <th className="py-2" />}
              </tr>
            </thead>
            <tbody>
              {office.part_c.length === 0 && (
                <tr>
                  <td
                    colSpan={canPartC ? 5 : 4}
                    className="py-6 text-center text-[var(--color-ink-faint)]"
                  >
                    No sections/units/cells under this office.
                  </td>
                </tr>
              )}
              {office.part_c.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-[var(--color-line)] last:border-0"
                >
                  <td className="py-2 pr-3 font-medium">
                    <Link
                      href={`/manage/org-units/${s.id}`}
                      className="text-[var(--color-green)] hover:underline"
                    >
                      {s.name}
                    </Link>
                  </td>
                  <td className="py-2 pr-3">
                    {orgUnitLabel("section", s.sub_kind)}
                  </td>
                  <td className="py-2 pr-3 text-[var(--color-ink-soft)]">
                    {s.officer_in_charge_name ?? "—"}
                  </td>
                  <td className="py-2 pr-3 text-right">
                    {s.headcount_note || s.employee_count}
                  </td>
                  {canPartC && (
                    <td className="py-2">
                      <button
                        onClick={() => deleteSection(s)}
                        className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-danger)] hover:bg-[#fbf0f0]"
                        title="Deactivate"
                      >
                        <Trash2 size={14} /> <span>Deactivate</span>
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add section modal */}
      <Modal
        open={secOpen}
        onClose={() => setSecOpen(false)}
        title="Add section / unit / cell"
      >
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="label">Name *</label>
              <input
                className="input"
                value={secForm.name}
                onChange={(e) =>
                  setSecForm((f) => ({ ...f, name: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="label">Type</label>
              <select
                className="input"
                value={secForm.sub_kind}
                onChange={(e) =>
                  setSecForm((f) => ({ ...f, sub_kind: e.target.value }))
                }
              >
                <option value="section">Section</option>
                <option value="unit">Unit</option>
                <option value="cell">Cell</option>
              </select>
            </div>
            <div>
              <label className="label">Headcount note</label>
              <input
                className="input"
                value={secForm.headcount_note}
                onChange={(e) =>
                  setSecForm((f) => ({
                    ...f,
                    headcount_note: e.target.value,
                  }))
                }
              />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Officer-in-charge (employee ID)</label>
              <input
                className="input"
                placeholder="numeric employee id"
                value={secForm.officer_in_charge_employee_id}
                onChange={(e) =>
                  setSecForm((f) => ({
                    ...f,
                    officer_in_charge_employee_id: e.target.value,
                  }))
                }
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 border-t border-[var(--color-line)] pt-4">
            <button onClick={() => setSecOpen(false)} className="btn btn-ghost">
              Cancel
            </button>
            <button
              onClick={saveSection}
              className="btn btn-primary"
              disabled={busy || !secForm.name.trim()}
            >
              {busy ? <Spinner /> : "Add"}
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
