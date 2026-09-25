"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Pencil, Plus, Power } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { orgUnitLabel } from "@/lib/format";
import { SectionTitle, Spinner, StatusBadge } from "@/components/ui";

interface OrgUnit {
  id: number;
  kind: string;
  sub_kind: string;
  parent_id: number | null;
  parent_name: string | null;
  college_id: number | null;
  college_name: string | null;
  name: string;
  short_code: string;
  code: string;
  location_id: number | null;
  location_name: string | null;
  is_active: boolean;
  path: string;
  head_employee_id: number | null;
  head_name: string | null;
  officer_in_charge_employee_id: number | null;
  officer_in_charge_name: string | null;
  headcount_note: string;
  direct_employee_count: number;
  employee_count: number;
  sanctioned_count: number;
  child_count: number;
}

interface LocationOption {
  id: number;
  name: string;
}

const KINDS = ["university", "college", "establishment", "department", "section"] as const;
const KIND_SORT_ORDER: Record<string, number> = {
  university: 0,
  college: 1,
  establishment: 2,
  department: 2,
  section: 3,
};
// Mirrors backend app.services.org.VALID_PARENT_KINDS — which parent kinds
// a given kind may attach to (sections/units/cells are edited elsewhere).
const VALID_PARENT_KINDS_BY_KIND: Record<string, string[]> = {
  college: ["university"],
  establishment: ["college", "university"],
  department: ["college", "establishment", "university"],
};
const SUB_KINDS = ["section", "unit", "cell"];

const BLANK = {
  kind: "establishment",
  sub_kind: "section",
  parent_id: "",
  name: "",
  short_code: "",
  location_id: "",
  reporting_authority_text: "",
  hrms_contact_name: "",
  hrms_contact_designation: "",
  hrms_contact_phone: "",
  hrms_contact_email: "",
  office_email: "",
  officer_in_charge_employee_id: "",
  headcount_note: "",
  description: "",
};

type Form = typeof BLANK;

export default function ManageOrgUnitsPage() {
  const { can } = useAuth();
  const { push } = useToast();
  const { data, loading, reload } = useApi<OrgUnit[]>(
    "/api/org-units?include_inactive=true&limit=1000"
  );
  const { data: locations } = useApi<LocationOption[]>("/api/locations");

  const [kindFilter, setKindFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<OrgUnit | null>(null);
  const [form, setForm] = useState<Form>({ ...BLANK });
  const [busy, setBusy] = useState(false);

  const canStructure = can(P.structureManage);
  const canSection = can(P.orgCreate) || can(P.orgEdit);
  const canManage = (kind: string) => kind === "section" ? canSection : canStructure;

  const rows = data ?? [];
  const parentOptions = useMemo(
    () =>
      rows
        .filter((u) => u.kind !== "section")
        .sort((a, b) => {
          // Group by tier first (University, then Colleges, then
          // Establishments/Departments) so unrelated branches never
          // interleave with each other just because their path strings
          // happen to sort next to one another alphabetically.
          const tierDiff =
            (KIND_SORT_ORDER[a.kind] ?? 9) - (KIND_SORT_ORDER[b.kind] ?? 9);
          if (tierDiff !== 0) return tierDiff;
          return a.path.localeCompare(b.path);
        }),
    [rows]
  );
  const filtered = kindFilter
    ? rows.filter((r) => r.kind === kindFilter)
    : rows;

  function openCreate() {
    setEditing(null);
    setForm({ ...BLANK });
    setOpen(true);
  }

  function openEdit(u: OrgUnit) {
    setEditing(u);
    setForm({
      kind: u.kind,
      sub_kind: u.sub_kind || "section",
      parent_id: String(u.parent_id ?? ""),
      name: u.name,
      short_code: u.short_code,
      location_id: String(u.location_id ?? ""),
      reporting_authority_text: "",
      hrms_contact_name: "",
      hrms_contact_designation: "",
      hrms_contact_phone: "",
      hrms_contact_email: "",
      office_email: "",
      officer_in_charge_employee_id: String(u.officer_in_charge_employee_id ?? ""),
      headcount_note: u.headcount_note ?? "",
      description: "",
    });
    setOpen(true);
  }

  function set<K extends keyof Form>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function save() {
    setBusy(true);
    const isSection = form.kind === "section";
    const payload: Record<string, unknown> = {
      kind: form.kind,
      name: form.name.trim(),
      short_code: form.short_code.trim().toUpperCase() || undefined,
      parent_id: form.parent_id ? Number(form.parent_id) : null,
      location_id: form.location_id ? Number(form.location_id) : null,
      description: form.description,
    };
    if (isSection) {
      payload.sub_kind = form.sub_kind;
      payload.headcount_note = form.headcount_note;
      payload.officer_in_charge_employee_id = form.officer_in_charge_employee_id
        ? Number(form.officer_in_charge_employee_id)
        : null;
    } else {
      payload.reporting_authority_text = form.reporting_authority_text;
      payload.hrms_contact_name = form.hrms_contact_name;
      payload.hrms_contact_designation = form.hrms_contact_designation;
      payload.hrms_contact_phone = form.hrms_contact_phone;
      payload.hrms_contact_email = form.hrms_contact_email;
      payload.office_email = form.office_email;
    }
    try {
      if (editing) {
        await api.put(`/api/org-units/${editing.id}`, payload);
        push("success", "Org unit updated");
      } else {
        await api.post("/api/org-units", payload);
        push("success", "Org unit created");
      }
      setOpen(false);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(u: OrgUnit) {
    try {
      if (u.is_active) {
        await api.del(`/api/org-units/${u.id}`);
        push("success", `${u.name} deactivated`);
      } else {
        await api.put(`/api/org-units/${u.id}`, { is_active: true });
        push("success", `${u.name} reactivated`);
      }
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  const [cleaningUp, setCleaningUp] = useState(false);
  const legacyAvfu = rows.find(
    (r) =>
      r.kind === "college" &&
      (r.code?.toLowerCase() === "avfu" ||
        r.short_code?.toLowerCase() === "avfu" ||
        r.name.toLowerCase().includes("assam veterinary and fishery university"))
  );

  async function promoteAvfuToUniversity() {
    setCleaningUp(true);
    try {
      const result = await api.post<{
        status: string;
        reparented_colleges?: string[];
        reparented_offices?: string[];
      }>("/api/org-units/promote-avfu-to-university");
      if (result.status === "noop") {
        push("success", "Already done — AVFU is already the university");
      } else {
        const collegeCount = result.reparented_colleges?.length ?? 0;
        const officeCount = result.reparented_offices?.length ?? 0;
        push(
          "success",
          `AVFU is now the University. Moved ${collegeCount} college(s) and ${officeCount} central office(s) to sit directly under it.`
        );
      }
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not update");
    } finally {
      setCleaningUp(false);
    }
  }

  const columns: Column<OrgUnit>[] = [
    {
      header: "Name",
      className: "min-w-[240px]",
      value: (r) => `${r.name} ${r.short_code} ${r.college_name ?? ""}`,
      cell: (r) => (
        <div>
          {r.kind === "college" ? (
            <span className="font-semibold">{r.name}</span>
          ) : (
            <Link
              href={`/manage/org-units/${r.id}`}
              className="font-semibold text-[var(--color-green)] hover:underline"
            >
              {r.name}
            </Link>
          )}
          <p className="text-xs text-[var(--color-ink-faint)]">
            {r.parent_name ? `under ${r.parent_name}` : "top level"}
            {r.short_code ? ` · ${r.short_code}` : ""}
            {r.college_name && r.college_name !== r.name && r.college_name !== r.parent_name
              ? ` · ${r.college_name}`
              : ""}
          </p>
        </div>
      ),
    },
    {
      header: "Kind",
      className: "w-32 whitespace-nowrap",
      value: (r) => r.kind,
      cell: (r) => orgUnitLabel(r.kind, r.sub_kind),
    },
    {
      header: "Campus",
      className: "w-40",
      value: (r) => r.location_name ?? "",
      cell: (r) => r.location_name ?? "—",
    },
    {
      header: "Head / OIC",
      className: "w-44",
      value: (r) => r.head_name ?? r.officer_in_charge_name ?? "",
      cell: (r) => r.head_name ?? r.officer_in_charge_name ?? "—",
    },
    {
      header: "Staff",
      className: "w-24 text-center whitespace-nowrap",
      value: (r) => r.employee_count,
      cell: (r) => (
        <span title={`${r.employee_count} employee(s), ${r.child_count} sub-unit(s)`}>
          {r.employee_count}
          {r.child_count > 0 && (
            <span className="text-[var(--color-ink-faint)]"> · {r.child_count} sub</span>
          )}
        </span>
      ),
    },
    {
      header: "Status",
      className: "w-28 whitespace-nowrap",
      value: (r) => (r.is_active ? "active" : "inactive"),
      cell: (r) => (
        <StatusBadge status={r.is_active ? "active" : "cancelled"} />
      ),
    },
    {
      header: "",
      className: "w-40 whitespace-nowrap",
      value: () => "",
      cell: (r) =>
        canManage(r.kind) ? (
          <div className="flex flex-nowrap gap-1.5">
            <button
              onClick={() => openEdit(r)}
              className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
              title="Edit"
            >
              <Pencil size={15} /> <span>Edit</span>
            </button>
            <button
              onClick={() => toggleActive(r)}
              className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-danger)] hover:bg-[#fbf0f0]"
              title={r.is_active ? "Deactivate" : "Reactivate"}
            >
              <Power size={15} /> <span>{r.is_active ? "Deactivate" : "Reactivate"}</span>
            </button>
          </div>
        ) : null,
    },
  ];

  const isSection = form.kind === "section";

  return (
    <>
      <SectionTitle
        title="Organisation Structure"
        subtitle="Colleges, Establishments, Departments and their Sections/Units/Cells. Open an Establishment or Department to edit its Part A / B / C."
      />

      {legacyAvfu && canStructure && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--color-danger)] bg-[#fbf0f0] p-4">
          <p className="text-sm text-[var(--color-ink)]">
            <strong>&quot;{legacyAvfu.name}&quot;</strong> is listed here as a
            College, but it&apos;s the University — the whole thing everything
            else sits under, not one org among others. Fixing this makes it
            the top-level University and moves CVSc, CFSc, LCVSc and the
            central offices (VC Office, Registrar, Comptroller, etc.) to sit
            directly under it, where they belong. Nothing is deleted.
          </p>
          <button
            onClick={promoteAvfuToUniversity}
            disabled={cleaningUp}
            className="btn btn-primary shrink-0"
            style={{ background: "var(--color-danger)" }}
          >
            {cleaningUp ? <Spinner /> : "Make AVFU the University"}
          </button>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <select
          className="input w-56"
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value)}
        >
          <option value="">All kinds</option>
          {KINDS.map((k) => (
            <option key={k} value={k}>
              {orgUnitLabel(k)}
            </option>
          ))}
        </select>
        {(canStructure || canSection) && (
          <button onClick={openCreate} className="btn btn-primary">
            <Plus size={16} /> Add unit
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size={28} />
        </div>
      ) : (
        <DataTable rows={filtered} columns={columns} />
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? "Edit org unit" : "Add org unit"}
        wide={!isSection}
      >
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Kind *</label>
              <select
                className="input"
                value={form.kind}
                onChange={(e) => set("kind", e.target.value)}
                disabled={!!editing}
              >
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {orgUnitLabel(k)}
                  </option>
                ))}
              </select>
            </div>
            {isSection && (
              <div>
                <label className="label">Section type</label>
                <select
                  className="input"
                  value={form.sub_kind}
                  onChange={(e) => set("sub_kind", e.target.value)}
                >
                  {SUB_KINDS.map((s) => (
                    <option key={s} value={s}>
                      {orgUnitLabel("section", s)}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className="sm:col-span-2">
              <label className="label">Name *</label>
              <input
                className="input"
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
              />
            </div>
            {form.kind !== "section" && (
              <div>
                <label className="label">
                  Short code {form.kind !== "department" ? "*" : ""}
                </label>
                <input
                  className="input font-mono uppercase"
                  maxLength={20}
                  placeholder="e.g. DOR"
                  value={form.short_code}
                  onChange={(e) => set("short_code", e.target.value)}
                />
                <p className="mt-1 text-xs text-[var(--color-ink-faint)]">
                  Used in Employee IDs: AVFU/&lt;establishment&gt;/&lt;dept|GEN&gt;/####
                </p>
              </div>
            )}
            {form.kind !== "university" && (
              <div>
                <label className="label">
                  Parent {form.kind === "college" ? "" : "*"}
                </label>
                <select
                  className="input"
                  value={form.parent_id}
                  onChange={(e) => set("parent_id", e.target.value)}
                >
                  <option value="">
                    {form.kind === "college" ? "None (independent)" : "Select…"}
                  </option>
                  {parentOptions
                    .filter((p) =>
                      (VALID_PARENT_KINDS_BY_KIND[form.kind] ?? []).includes(p.kind)
                    )
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {orgUnitLabel(p.kind)}: {p.path}
                      </option>
                    ))}
                </select>
              </div>
            )}
            <div>
              <label className="label">Campus</label>
              <select
                className="input"
                value={form.location_id}
                onChange={(e) => set("location_id", e.target.value)}
              >
                <option value="">—</option>
                {(locations ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {!isSection && (
            <div className="grid gap-4 border-t border-[var(--color-line)] pt-4 sm:grid-cols-2">
              <p className="sm:col-span-2 text-sm font-semibold text-[var(--color-ink-muted)]">
                Part A — General Information
              </p>
              <div className="sm:col-span-2">
                <label className="label">Reporting authority</label>
                <input
                  className="input"
                  placeholder="e.g. Vice-Chancellor / Registrar, AVFU"
                  value={form.reporting_authority_text}
                  onChange={(e) => set("reporting_authority_text", e.target.value)}
                />
              </div>
              <div>
                <label className="label">HRMS contact name</label>
                <input
                  className="input"
                  value={form.hrms_contact_name}
                  onChange={(e) => set("hrms_contact_name", e.target.value)}
                />
              </div>
              <div>
                <label className="label">HRMS contact designation</label>
                <input
                  className="input"
                  value={form.hrms_contact_designation}
                  onChange={(e) =>
                    set("hrms_contact_designation", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="label">HRMS contact phone</label>
                <input
                  className="input"
                  value={form.hrms_contact_phone}
                  onChange={(e) => set("hrms_contact_phone", e.target.value)}
                />
              </div>
              <div>
                <label className="label">HRMS contact email</label>
                <input
                  className="input"
                  value={form.hrms_contact_email}
                  onChange={(e) => set("hrms_contact_email", e.target.value)}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="label">Office email</label>
                <input
                  className="input"
                  value={form.office_email}
                  onChange={(e) => set("office_email", e.target.value)}
                />
              </div>
            </div>
          )}

          {isSection && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Officer-in-charge (employee ID)</label>
                <input
                  className="input"
                  placeholder="numeric employee id"
                  value={form.officer_in_charge_employee_id}
                  onChange={(e) =>
                    set("officer_in_charge_employee_id", e.target.value)
                  }
                />
              </div>
              <div>
                <label className="label">Headcount note</label>
                <input
                  className="input"
                  value={form.headcount_note}
                  onChange={(e) => set("headcount_note", e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-[var(--color-line)] pt-4">
            <button onClick={() => setOpen(false)} className="btn btn-ghost">
              Cancel
            </button>
            <button
              onClick={save}
              className="btn btn-primary"
              disabled={busy || !form.name.trim()}
            >
              {busy ? <Spinner /> : editing ? "Save changes" : "Create"}
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
