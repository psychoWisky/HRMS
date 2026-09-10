"use client";

import { useMemo, useState } from "react";
import { Download, FileBarChart2, FileSpreadsheet } from "lucide-react";
import { downloadFile } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useToast } from "@/components/Toast";
import { ApiError } from "@/lib/api";
import { Column, DataTable } from "@/components/DataTable";
import { SectionTitle } from "@/components/ui";

interface ReportDef {
  key: string;
  title: string;
}

interface ReportData {
  title: string;
  columns: string[];
  rows: (string | number)[][];
}

interface ReportRow {
  id: number;
  cells: (string | number)[];
}

interface Option {
  id: number;
  name: string;
}

const STATUS_OPTIONS = ["active", "inactive", "retired", "transferred"];

const FILTER_BLANK = {
  establishment_id: "",
  location_id: "",
  pay_scale: "",
  employment_status: "",
  joined_from: "",
  joined_to: "",
  promoted_from: "",
  promoted_to: "",
};

function useReportTable(data: ReportData | null | undefined) {
  const rows: ReportRow[] = useMemo(
    () => (data?.rows ?? []).map((cells, i) => ({ id: i, cells })),
    [data]
  );
  const columns: Column<ReportRow>[] = useMemo(
    () =>
      (data?.columns ?? []).map((header, index) => ({
        header,
        value: (r) => r.cells[index],
        cell: (r) => r.cells[index],
      })),
    [data]
  );
  return { rows, columns };
}

export default function ReportsPage() {
  const { push } = useToast();
  const [tab, setTab] = useState<"fixed" | "employees">("employees");

  // --- Fixed reports (existing views) ---
  const { data: reports } = useApi<ReportDef[]>("/api/dashboard/reports");
  const [selected, setSelected] = useState("employees-by-organization");
  const { data: fixedData, loading: fixedLoading } = useApi<ReportData>(
    tab === "fixed" ? `/api/dashboard/reports/${selected}` : null
  );
  const fixedTable = useReportTable(fixedData);

  async function downloadFixed() {
    try {
      await downloadFile(
        `/api/dashboard/reports/${selected}/export`,
        `avfu-${selected}.xlsx`
      );
      push("success", "Report downloaded");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Download failed");
    }
  }

  // --- Filterable employee report (combinable filters) ---
  const [filters, setFilters] = useState({ ...FILTER_BLANK });
  const { data: establishments } = useApi<Option[]>("/api/org-units?kind=establishment");
  const { data: locations } = useApi<Option[]>("/api/locations");

  const filterQuery = useMemo(() => {
    const params = new URLSearchParams();
    if (filters.establishment_id) params.set("establishment_id", filters.establishment_id);
    if (filters.location_id) params.set("location_id", filters.location_id);
    if (filters.pay_scale) params.set("pay_scale", filters.pay_scale);
    if (filters.employment_status) params.set("employment_status", filters.employment_status);
    if (filters.joined_from) params.set("joined_from", filters.joined_from);
    if (filters.joined_to) params.set("joined_to", filters.joined_to);
    if (filters.promoted_from) params.set("promoted_from", filters.promoted_from);
    if (filters.promoted_to) params.set("promoted_to", filters.promoted_to);
    return params.toString();
  }, [filters]);

  const { data: empData, loading: empLoading } = useApi<ReportData>(
    tab === "employees"
      ? `/api/dashboard/reports-employees/filtered?${filterQuery}`
      : null
  );
  const empTable = useReportTable(empData);

  async function downloadEmployees() {
    try {
      await downloadFile(
        `/api/dashboard/reports-employees/filtered/export?${filterQuery}`,
        "avfu-employee-report.xlsx"
      );
      push("success", "Report downloaded");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Download failed");
    }
  }

  return (
    <>
      <SectionTitle
        title="Reports"
        subtitle="University-wide reports generated live from HRMS data. Every report downloads as Excel (.xlsx)."
      />

      <div className="mb-5 flex gap-2">
        {(["employees", "fixed"] as const).map((t) => (
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
            {t === "employees" ? "Employee Report (filters)" : "Standard Reports"}
          </button>
        ))}
      </div>

      {tab === "employees" ? (
        <>
          <div className="card mb-5 p-4">
            <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-[var(--color-ink-faint)]">
              Combine filters
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="label">Establishment</label>
                <select
                  className="input"
                  value={filters.establishment_id}
                  onChange={(e) =>
                    setFilters({ ...filters, establishment_id: e.target.value })
                  }
                >
                  <option value="">All</option>
                  {(establishments ?? []).map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Campus</label>
                <select
                  className="input"
                  value={filters.location_id}
                  onChange={(e) => setFilters({ ...filters, location_id: e.target.value })}
                >
                  <option value="">All</option>
                  {(locations ?? []).map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Pay Scale</label>
                <input
                  className="input"
                  value={filters.pay_scale}
                  onChange={(e) => setFilters({ ...filters, pay_scale: e.target.value })}
                  placeholder="Exact match"
                />
              </div>
              <div>
                <label className="label">Employee status</label>
                <select
                  className="input"
                  value={filters.employment_status}
                  onChange={(e) =>
                    setFilters({ ...filters, employment_status: e.target.value })
                  }
                >
                  <option value="">All</option>
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s[0].toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Joined from</label>
                <input
                  className="input"
                  type="date"
                  value={filters.joined_from}
                  onChange={(e) => setFilters({ ...filters, joined_from: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Joined to</label>
                <input
                  className="input"
                  type="date"
                  value={filters.joined_to}
                  onChange={(e) => setFilters({ ...filters, joined_to: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Promoted from</label>
                <input
                  className="input"
                  type="date"
                  value={filters.promoted_from}
                  onChange={(e) =>
                    setFilters({ ...filters, promoted_from: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="label">Promoted to</label>
                <input
                  className="input"
                  type="date"
                  value={filters.promoted_to}
                  onChange={(e) => setFilters({ ...filters, promoted_to: e.target.value })}
                />
              </div>
            </div>
            <button
              onClick={() => setFilters({ ...FILTER_BLANK })}
              className="btn btn-ghost mt-3 px-4 py-2 text-sm"
            >
              Clear filters
            </button>
          </div>

          <div className="card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-[var(--color-green)]">
                <FileBarChart2 size={20} />
                <h3 className="text-lg font-bold text-[var(--color-ink)]">
                  {empData?.title ?? "Employee report"}
                </h3>
              </div>
              <button
                onClick={downloadEmployees}
                className="btn btn-primary px-4 py-2 text-sm"
                disabled={!empData || empData.rows.length === 0}
              >
                <FileSpreadsheet size={16} /> Download Excel
              </button>
            </div>
            <DataTable
              columns={empTable.columns}
              rows={empTable.rows}
              loading={empLoading}
              empty="No employees match these filters"
              searchPlaceholder="Search within results"
              pageSize={25}
            />
          </div>
        </>
      ) : (
        <>
          <div className="card mb-5 p-4">
            <div className="flex flex-wrap gap-2">
              {(reports ?? []).map((r) => (
                <button
                  key={r.key}
                  onClick={() => setSelected(r.key)}
                  className="rounded-full border px-4 py-2 text-sm font-semibold transition-colors"
                  style={{
                    borderColor:
                      selected === r.key ? "var(--color-green)" : "var(--color-line)",
                    background:
                      selected === r.key ? "var(--color-green)" : "transparent",
                    color: selected === r.key ? "#fff" : "var(--color-ink-soft)",
                  }}
                >
                  {r.title}
                </button>
              ))}
            </div>
          </div>

          <div className="card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-[var(--color-green)]">
                <FileBarChart2 size={20} />
                <h3 className="text-lg font-bold text-[var(--color-ink)]">
                  {fixedData?.title ?? "Report"}
                </h3>
              </div>
              <button
                onClick={downloadFixed}
                className="btn btn-ghost px-4 py-2 text-sm"
                disabled={!fixedData || fixedData.rows.length === 0}
              >
                <Download size={16} /> Download Excel
              </button>
            </div>

            <DataTable
              key={selected}
              columns={fixedTable.columns}
              rows={fixedTable.rows}
              loading={fixedLoading}
              empty="This report has no rows yet"
              searchPlaceholder="Search within this report"
              pageSize={25}
            />
          </div>
        </>
      )}
    </>
  );
}
