"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Building2, Search, Users } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { OrgUnitSelect } from "@/components/OrgUnitSelect";
import { Avatar, Empty, SectionTitle, Skeleton } from "@/components/ui";

interface EmployeeSummary {
  id: number;
  hrms_employee_id: string;
  full_name: string;
  college: string | null;
  department: string | null;
  establishment: string | null;
  designation: string | null;
  organization: string | null;
  organization_path: string;
  location: string | null;
  official_email: string;
  phone: string;
  reports_to: string | null;
  reports_to_id: number | null;
}

interface LocationOption {
  id: number;
  name: string;
}

export default function DirectoryPage() {
  const { user } = useAuth();
  const isDeptHead = user?.role === "department_head";

  const [query, setQuery] = useState("");
  const [orgId, setOrgId] = useState("");
  const [locationId, setLocationId] = useState("");

  const path = useMemo(() => {
    const params = new URLSearchParams({ limit: "500" });
    if (query.trim()) params.set("q", query.trim());
    if (orgId) params.set("org_unit_id", orgId);
    if (locationId) params.set("location_id", locationId);
    return `/api/directory?${params.toString()}`;
  }, [query, orgId, locationId]);

  const { data, loading } = useApi<EmployeeSummary[]>(path);
  const { data: locations } = useApi<LocationOption[]>("/api/locations");

  const rows = data ?? [];

  return (
    <>
      <SectionTitle
        title={isDeptHead ? "Department Directory" : "AVFU Employee Directory"}
        subtitle={
          isDeptHead
            ? `Employees of ${user?.managed_org_unit_name ?? "your department"}. Select a person to see where they sit and who they report to.`
            : "Every employee of the university, across all campuses and offices. Select a person to see where they sit and who they report to."
        }
      />

      <div className="card mb-6 p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <div className="relative">
            <Search
              size={19}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]"
            />
            <input
              className="input pl-11"
              placeholder="Search by name, HRMS ID or email"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          {!isDeptHead && (
            <OrgUnitSelect
              className="md:w-64"
              value={orgId ? Number(orgId) : null}
              onChange={(id) => setOrgId(id ? String(id) : "")}
              placeholder="All establishments / departments"
            />
          )}
          <select
            className="input md:w-52"
            value={locationId}
            onChange={(e) => setLocationId(e.target.value)}
          >
            <option value="">All campuses</option>
            {(locations ?? []).map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-sm text-[var(--color-ink-faint)]">
          <Users size={16} />
          {loading ? "Loading…" : `${rows.length} employee${rows.length === 1 ? "" : "s"}`}
        </p>
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <Empty message="No employees match those filters" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((e) => (
            <Link
              key={e.id}
              href={`/directory/${e.id}`}
              className="card block p-5 transition-shadow hover:shadow-[var(--shadow-md)]"
            >
              <div className="flex items-start gap-3">
                <Avatar name={e.full_name} size={46} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-[var(--color-ink)]">
                    {e.full_name}
                  </p>
                  <p className="truncate text-sm text-[var(--color-ink-soft)]">
                    {e.designation ?? "Designation not assigned"}
                  </p>
                  <p className="mt-0.5 font-mono text-xs text-[var(--color-ink-faint)]">
                    {e.hrms_employee_id}
                  </p>
                </div>
              </div>
              <div className="mt-4 space-y-1 border-t border-[var(--color-line)] pt-3 text-xs">
                {e.college && (
                  <p className="truncate text-[var(--color-ink-soft)]">
                    <span className="font-semibold text-[var(--color-ink-muted)]">College:</span> {e.college}
                  </p>
                )}
                {e.department && (
                  <p className="truncate text-[var(--color-ink-soft)]">
                    <span className="font-semibold text-[var(--color-ink-muted)]">Department:</span> {e.department}
                  </p>
                )}
                {e.establishment && (
                  <p className="truncate text-[var(--color-ink-soft)]">
                    <span className="font-semibold text-[var(--color-ink-muted)]">Establishment:</span> {e.establishment}
                  </p>
                )}
                {!e.college && !e.department && !e.establishment && (
                  <p className="flex items-start gap-1.5 text-[var(--color-ink-soft)]">
                    <Building2 size={15} className="mt-0.5 shrink-0" />
                    <span className="truncate">{e.organization ?? "—"}</span>
                  </p>
                )}
                <p className="text-[var(--color-ink-faint)]">
                  Reports to:{" "}
                  <span className="text-[var(--color-ink-soft)]">
                    {e.reports_to ?? "—"}
                  </span>
                </p>
                {e.location && (
                  <p className="text-[var(--color-ink-faint)]">{e.location}</p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
