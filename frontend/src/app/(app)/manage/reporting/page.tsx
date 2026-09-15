"use client";

import { useState } from "react";
import { AlertTriangle, Network, Trash2, UserCog } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { titleize } from "@/lib/format";
import { Empty, SectionTitle, Spinner } from "@/components/ui";
import { SearchableSelect } from "@/components/SearchableSelect";

interface EmployeeRow {
  id: number;
  hrms_employee_id: string;
  full_name: string;
  designation: string | null;
  organization: string | null;
  reports_to: string | null;
  reports_to_id: number | null;
}

interface ReportingLink {
  id: number;
  employee_id: number;
  employee_name: string;
  reports_to_id: number;
  reports_to_name: string;
  reports_to_designation: string | null;
  relationship_type: string;
  is_primary: boolean;
}

export default function ManageReportingPage() {
  const { can } = useAuth();
  const { push } = useToast();
  const canManage = can(P.reportingManage);

  const { data, loading, reload } = useApi<EmployeeRow[]>(
    "/api/directory?limit=1000"
  );
  const everyone = data;

  const [target, setTarget] = useState<EmployeeRow | null>(null);
  const [managerId, setManagerId] = useState("");
  const [relType, setRelType] = useState("administrative");
  const [isPrimary, setIsPrimary] = useState(true);
  const [busy, setBusy] = useState(false);

  const { data: links, reload: reloadLinks } = useApi<ReportingLink[]>(
    target ? `/api/reporting?employee_id=${target.id}` : null
  );

  async function assign() {
    if (!target || !managerId) return;
    setBusy(true);
    try {
      await api.post("/api/reporting", {
        employee_id: target.id,
        reports_to_id: Number(managerId),
        relationship_type: relType,
        is_primary: isPrimary,
      });
      push("success", "Reporting relationship saved");
      setManagerId("");
      reloadLinks();
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  async function removeLink(link: ReportingLink) {
    setBusy(true);
    try {
      await api.del(`/api/reporting/${link.id}`);
      push("success", "Reporting relationship removed");
      reloadLinks();
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Could not remove");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<EmployeeRow>[] = [
    {
      header: "Employee",
      value: (r) => `${r.full_name} ${r.hrms_employee_id}`,
      cell: (r) => (
        <div>
          <p className="font-semibold">{r.full_name}</p>
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
      header: "Reports to",
      value: (r) => r.reports_to ?? "",
      cell: (r) =>
        r.reports_to ? (
          r.reports_to
        ) : (
          <span className="text-[var(--color-ink-faint)]">Not assigned</span>
        ),
    },
    {
      header: "",
      cell: (r) =>
        canManage ? (
          <button
            onClick={() => {
              setTarget(r);
              setManagerId("");
              setIsPrimary(true);
            }}
            className="btn btn-ghost px-3 py-1.5 text-sm"
          >
            <UserCog size={16} /> Manage
          </button>
        ) : null,
    },
  ];

  return (
    <>
      <SectionTitle
        title="Reporting Hierarchy"
        subtitle="Set who reports to whom. Circular relationships are rejected, and exactly one authority per employee is the primary one."
      />

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No employees recorded"
        searchPlaceholder="Search employee, HRMS ID, designation or reporting authority"
      />

      <Modal
        open={!!target}
        onClose={() => setTarget(null)}
        title={target ? `Reporting for ${target.full_name}` : ""}
        wide
      >
        {target && (
          <div className="space-y-5">
            <div className="rounded-xl bg-[var(--color-surface-2)] p-4">
              <p className="font-semibold">{target.full_name}</p>
              <p className="text-sm text-[var(--color-ink-soft)]">
                {target.designation ?? "—"}
                {target.organization ? ` · ${target.organization}` : ""}
              </p>
            </div>

            <div>
              <h4 className="mb-3 font-bold">Current reporting authorities</h4>
              {(links ?? []).length === 0 ? (
                <Empty message="No reporting authority assigned" />
              ) : (
                <ul className="space-y-2">
                  {(links ?? []).map((l) => (
                    <li
                      key={l.id}
                      className="flex items-center gap-3 rounded-xl border border-[var(--color-line)] p-3"
                    >
                      <Network size={18} className="text-[var(--color-green)]" />
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold">{l.reports_to_name}</p>
                        <p className="text-xs text-[var(--color-ink-faint)]">
                          {l.reports_to_designation ?? "—"} ·{" "}
                          {titleize(l.relationship_type)}
                          {l.is_primary ? " · Primary" : ""}
                        </p>
                      </div>
                      <button
                        onClick={() => removeLink(l)}
                        className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-danger)] hover:bg-[#fbf0f0]"
                        title="Remove"
                        disabled={busy}
                      >
                        <Trash2 size={15} /> <span>Remove</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl bg-[var(--color-surface-2)] p-4">
              <h4 className="mb-3 font-bold">Assign a reporting authority</h4>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="label">Reports to</label>
                  <SearchableSelect
                    value={managerId}
                    onChange={setManagerId}
                    placeholder="Select an employee..."
                    searchPlaceholder="Search employees..."
                    options={(everyone ?? [])
                      .filter((e) => e.id !== target.id)
                      .map((e) => ({
                        value: String(e.id),
                        label: `${e.full_name}${e.designation ? ` - ${e.designation}` : ""}`,
                      }))}
                  />
                </div>
                <div>
                  <label className="label">Relationship type</label>
                  <select
                    className="input"
                    value={relType}
                    onChange={(e) => setRelType(e.target.value)}
                  >
                    <option value="administrative">Administrative</option>
                    <option value="functional">Functional</option>
                  </select>
                </div>
                <label className="flex items-end gap-2 pb-3 text-sm text-[var(--color-ink-soft)]">
                  <input
                    type="checkbox"
                    checked={isPrimary}
                    onChange={(e) => setIsPrimary(e.target.checked)}
                  />
                  Primary reporting authority
                </label>
              </div>
              <button
                onClick={assign}
                className="btn btn-primary mt-3 w-full"
                disabled={busy || !managerId}
              >
                {busy ? <Spinner /> : "Save reporting relationship"}
              </button>
              <p className="mt-3 flex items-start gap-2 text-xs text-[var(--color-ink-faint)]">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                The system rejects any assignment that would make the hierarchy
                loop back on itself.
              </p>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
