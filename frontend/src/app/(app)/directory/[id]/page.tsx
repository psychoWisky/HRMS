"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronRight, Network } from "lucide-react";
import { useApi } from "@/lib/useApi";
import {
  Avatar,
  Empty,
  Field,
  MotionCard,
  SectionTitle,
  Skeleton,
} from "@/components/ui";

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
}

interface ReportingStructure {
  employee: EmployeeSummary;
  reports_to: EmployeeSummary | null;
  additional_authorities: EmployeeSummary[];
  reporting_chain: EmployeeSummary[];
  direct_reports: EmployeeSummary[];
}

function PersonRow({ person }: { person: EmployeeSummary }) {
  return (
    <Link
      href={`/directory/${person.id}`}
      className="flex items-center gap-3 rounded-xl border border-[var(--color-line)] bg-white p-3 transition-colors hover:border-[var(--color-green-soft)] hover:bg-[var(--color-green-tint)]"
    >
      <Avatar name={person.full_name} size={38} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-semibold text-[var(--color-ink)]">
          {person.full_name}
        </p>
        <p className="truncate text-sm text-[var(--color-ink-faint)]">
          {person.designation ?? "—"}
          {person.college ? ` · ${person.college}` : (person.organization ? ` · ${person.organization}` : "")}
        </p>
      </div>
    </Link>
  );
}

export default function DirectoryProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data, loading } = useApi<ReportingStructure>(`/api/directory/${id}`);

  if (loading) return <Skeleton className="h-96" />;
  if (!data) return <Empty message="Employee not found" />;

  const { employee, reports_to, additional_authorities, reporting_chain, direct_reports } =
    data;

  return (
    <>
      <Link
        href="/directory"
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--color-green)] hover:underline"
      >
        <ArrowLeft size={16} /> Back to directory
      </Link>

      <SectionTitle title={employee.full_name} subtitle={employee.organization_path} />

      <div className="grid gap-5 lg:grid-cols-3">
        <MotionCard className="lg:col-span-2">
          <div className="mb-5 flex items-center gap-4">
            <Avatar name={employee.full_name} size={64} />
            <div>
              <p className="text-xl font-bold">{employee.full_name}</p>
              <p className="text-[var(--color-ink-soft)]">
                {employee.designation ?? "Designation not assigned"}
              </p>
            </div>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="HRMS Employee ID" value={employee.hrms_employee_id} mono />
            <Field label="Designation" value={employee.designation} />
            <Field label="College" value={employee.college ?? "—"} />
            <Field label="Department" value={employee.department ?? "—"} />
            <Field label="Establishment" value={employee.establishment ?? "—"} />
            <Field label="Campus / Location" value={employee.location} />
            <Field label="Official Email" value={employee.official_email} />
            <Field label="Phone" value={employee.phone} />
          </div>
          <div className="mt-5 rounded-xl bg-[var(--color-surface-2)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
              Organisational position
            </p>
            <p className="mt-1 text-[15px]">{employee.organization_path || "—"}</p>
          </div>
        </MotionCard>

        <MotionCard>
          <div className="mb-4 flex items-center gap-2 text-[var(--color-green)]">
            <Network size={20} />
            <h3 className="text-lg font-bold text-[var(--color-ink)]">
              Reporting authority
            </h3>
          </div>
          {reports_to ? (
            <PersonRow person={reports_to} />
          ) : (
            <p className="text-sm text-[var(--color-ink-faint)]">
              No reporting authority recorded — this is a top-level position.
            </p>
          )}

          {additional_authorities.length > 0 && (
            <>
              <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                Also reports to
              </p>
              <div className="space-y-2">
                {additional_authorities.map((p) => (
                  <PersonRow key={p.id} person={p} />
                ))}
              </div>
            </>
          )}

          {reporting_chain.length > 0 && (
            <>
              <p className="mb-2 mt-5 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                Full reporting chain
              </p>
              <ol className="space-y-1 text-sm">
                {reporting_chain.map((p, i) => (
                  <li key={p.id} className="flex items-center gap-1.5">
                    <span
                      className="text-[var(--color-ink-faint)]"
                      style={{ paddingLeft: i * 10 }}
                    >
                      <ChevronRight size={14} />
                    </span>
                    <Link
                      href={`/directory/${p.id}`}
                      className="hover:underline"
                      style={{ color: "var(--color-green)" }}
                    >
                      {p.full_name}
                    </Link>
                    <span className="text-[var(--color-ink-faint)]">
                      {p.designation ? `· ${p.designation}` : ""}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          )}
        </MotionCard>
      </div>

      <MotionCard className="mt-5">
        <h3 className="mb-4 text-lg font-bold">
          Direct reports{" "}
          <span className="text-[var(--color-ink-faint)]">
            ({direct_reports.length})
          </span>
        </h3>
        {direct_reports.length === 0 ? (
          <Empty message="Nobody currently reports to this employee" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {direct_reports.map((p) => (
              <PersonRow key={p.id} person={p} />
            ))}
          </div>
        )}
      </MotionCard>
    </>
  );
}
