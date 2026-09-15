"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Building2,
  ClipboardCheck,
  IdCard,
  Inbox,
  MapPin,
  Network,
  ShieldCheck,
  UserCheck,
  Users,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { P } from "@/lib/perms";
import { fmtDate } from "@/lib/format";
import {
  Empty,
  Field,
  MotionCard,
  SectionTitle,
  Skeleton,
  StatTile,
} from "@/components/ui";

interface CountItem {
  label: string;
  count: number;
}

interface AdminDash {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
  total_organizations: number;
  total_locations: number;
  total_designations: number;
  sanctioned_posts: number;
  occupied_posts: number;
  vacant_posts: number;
  kyc_not_started: number;
  kyc_pending: number;
  kyc_verified: number;
  kyc_rejected: number;
  submissions_awaiting_review: number;
  submissions_approved: number;
  submissions_rejected: number;
  by_location: CountItem[];
  by_organization: CountItem[];
  by_designation: CountItem[];
}

interface OwnDash {
  hrms_employee_id: string;
  full_name: string;
  designation: string | null;
  organization: string | null;
  organization_path: string;
  location: string | null;
  reports_to: string | null;
  reports_to_designation: string | null;
  direct_reports_count: number;
  date_of_joining: string | null;
}

function BreakdownCard({
  title,
  items,
  icon: Icon,
}: {
  title: string;
  items: CountItem[];
  icon: React.ComponentType<{ size?: number }>;
}) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <MotionCard>
      <div className="mb-4 flex items-center gap-2 text-[var(--color-green)]">
        <Icon size={20} />
        <h3 className="text-lg font-bold text-[var(--color-ink)]">{title}</h3>
      </div>
      {items.length === 0 ? (
        <Empty message="No data yet" />
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.label}>
              <div className="mb-1 flex items-baseline justify-between gap-3">
                <span className="truncate text-[15px]">{item.label}</span>
                <span className="shrink-0 font-semibold text-[var(--color-green)]">
                  {item.count}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-[var(--color-surface-2)]">
                <div
                  className="h-1.5 rounded-full"
                  style={{
                    width: `${(item.count / max) * 100}%`,
                    background: "var(--color-green-soft)",
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </MotionCard>
  );
}

function AdminDashboard({ canReview }: { canReview: boolean }) {
  const { data, loading } = useApi<AdminDash>("/api/dashboard/admin");
  const [copied, setCopied] = useState(false);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }
  if (!data) return <Empty message="Dashboard unavailable" />;

  const fillRate = data.sanctioned_posts
    ? Math.round((data.occupied_posts / data.sanctioned_posts) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {canReview && (
        <div className="card flex flex-wrap items-center justify-between gap-4 border-l-4 p-5" style={{ borderLeftColor: "var(--color-green)" }}>
          <div>
            <p className="font-bold">New joinee submission link</p>
            <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
              Share this public URL with a new employee whenever needed.
            </p>
            <p className="mt-2 break-all font-mono text-sm text-[var(--color-green)]">
              {typeof window === "undefined" ? "/submit" : `${window.location.origin}/submit`}
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={async () => {
              const url = `${window.location.origin}/submit`;
              await navigator.clipboard.writeText(url);
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1800);
            }}
          >
            {copied ? "Copied" : "Copy URL"}
          </button>
        </div>
      )}
      {canReview && data.submissions_awaiting_review > 0 && (
        <Link
          href="/manage/submissions"
          className="card flex items-center gap-4 border-l-4 p-5 transition-shadow hover:shadow-[var(--shadow-md)]"
          style={{ borderLeftColor: "var(--color-warn)" }}
        >
          <Inbox size={26} style={{ color: "var(--color-warn)" }} />
          <div className="flex-1">
            <p className="text-lg font-bold">
              {data.submissions_awaiting_review} new employee submission
              {data.submissions_awaiting_review === 1 ? "" : "s"} awaiting review
            </p>
            <p className="text-sm text-[var(--color-ink-soft)]">
              Sent through the public document form. Verify and admit them into
              the HRMS.
            </p>
          </div>
          <span className="btn btn-primary px-4 py-2 text-sm">Review now</span>
        </Link>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Total Employees"
          value={data.total_employees}
          hint={`${data.active_employees} active · ${data.inactive_employees} inactive`}
          icon={Users}
        />
        <StatTile
          label="Sanctioned Posts"
          value={data.sanctioned_posts}
          hint={`${data.occupied_posts} occupied (${fillRate}% filled)`}
          icon={ClipboardCheck}
        />
        <StatTile
          label="Vacant Posts"
          value={data.vacant_posts}
          hint="Sanctioned minus occupied"
          icon={ClipboardCheck}
          tone="warn"
        />
        <StatTile
          label="Organisational Units"
          value={data.total_organizations}
          hint={`${data.total_locations} campuses · ${data.total_designations} designations`}
          icon={Building2}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Submissions To Review"
          value={data.submissions_awaiting_review}
          hint="From the public form"
          icon={Inbox}
          tone={data.submissions_awaiting_review ? "warn" : "default"}
        />
        <StatTile
          label="Admitted From Submissions"
          value={data.submissions_approved}
          icon={UserCheck}
        />
        <StatTile
          label="Documents Verified"
          value={data.kyc_verified}
          icon={ShieldCheck}
        />
        <StatTile
          label="Documents Outstanding"
          value={data.kyc_not_started + data.kyc_pending}
          hint={`${data.kyc_rejected} rejected`}
          icon={IdCard}
          tone={data.kyc_not_started + data.kyc_pending ? "warn" : "default"}
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <BreakdownCard
          title="Employees by campus"
          items={data.by_location}
          icon={MapPin}
        />
        <BreakdownCard
          title="Employees by establishment / department"
          items={data.by_organization}
          icon={Building2}
        />
        <BreakdownCard
          title="Employees by designation"
          items={data.by_designation}
          icon={ClipboardCheck}
        />
      </div>
    </div>
  );
}

/** Fallback for any login without full employee-management permissions
 *  (only reachable if Admin creates a custom restricted role — by default
 *  every account is either Admin or HR, both of which see AdminDashboard). */
function LimitedDashboard() {
  const { data, loading } = useApi<OwnDash>("/api/dashboard/me");

  if (loading) return <Skeleton className="h-64" />;
  if (!data) return <Empty message="Dashboard unavailable" />;

  return (
    <div className="space-y-6">
      <div
        className="rounded-2xl p-7 text-white"
        style={{
          background:
            "linear-gradient(120deg, var(--color-green-deep), var(--color-green-soft))",
        }}
      >
        <p className="text-white/80">Welcome to AVFU HRMS</p>
        <h2 className="mt-1 text-3xl font-bold">{data.full_name}</h2>
        <p className="mt-2 text-white/85">
          {data.designation ?? "Designation not assigned"}
          {data.organization ? ` · ${data.organization}` : ""}
        </p>
        <p className="mt-4 inline-block rounded-lg bg-white/15 px-3 py-1.5 font-mono text-sm">
          HRMS Employee ID: {data.hrms_employee_id}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <MotionCard className="lg:col-span-2">
          <h3 className="mb-4 text-lg font-bold">My office</h3>
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Employee ID" value={data.hrms_employee_id} mono />
            <Field label="Designation" value={data.designation} />
            <Field label="Organisation" value={data.organization} />
            <Field label="Campus / Location" value={data.location} />
            <Field
              label="Reporting Authority"
              value={
                data.reports_to
                  ? `${data.reports_to}${
                      data.reports_to_designation
                        ? ` (${data.reports_to_designation})`
                        : ""
                    }`
                  : "Not assigned"
              }
            />
            <Field label="Date of Joining" value={fmtDate(data.date_of_joining)} />
          </div>
          <div className="mt-5 rounded-xl bg-[var(--color-surface-2)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
              Position in AVFU
            </p>
            <p className="mt-1 text-[15px]">{data.organization_path || "—"}</p>
          </div>
        </MotionCard>

        <div className="space-y-5">
          <MotionCard>
            <div className="mb-3 flex items-center gap-2 text-[var(--color-green)]">
              <Network size={20} />
              <h3 className="text-lg font-bold text-[var(--color-ink)]">
                Staff under me
              </h3>
            </div>
            <p className="text-3xl font-bold text-[var(--color-green)]">
              {data.direct_reports_count}
            </p>
            <p className="text-sm text-[var(--color-ink-soft)]">
              direct report{data.direct_reports_count === 1 ? "" : "s"}
            </p>
            <Link href="/directory" className="btn btn-ghost mt-4 w-full">
              <UserCheck size={18} /> Employee directory
            </Link>
          </MotionCard>

        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user, can } = useAuth();
  const isAdmin = can(P.employeeRead) && can(P.employeeEdit);
  const isDeptHead = user?.role === "department_head";

  return (
    <>
      <SectionTitle
        title="Dashboard"
        subtitle={
          isDeptHead
            ? `Signed in as Department Head. Figures below cover only your department.`
            : isAdmin
              ? "University-wide position of employees, posts and document verification."
              : `Signed in as ${user?.role_name ?? "Staff"}.`
        }
      />
      {isAdmin ? (
        <AdminDashboard canReview={can(P.submissionReview)} />
      ) : (
        <LimitedDashboard />
      )}
    </>
  );
}
