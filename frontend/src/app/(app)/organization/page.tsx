"use client";

import { useMemo, useState } from "react";
import { Building2, Search } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { OrgChart, type OrgNode } from "@/components/OrgChart";
import { UniversityOrganogram } from "@/components/UniversityOrganogram";
import { Empty, SectionTitle, Skeleton } from "@/components/ui";

const DEPTH_OPTIONS = [
  { value: 1, label: "Top level" },
  { value: 2, label: "2 levels" },
  { value: 3, label: "3 levels" },
  { value: 9, label: "Everything" },
];

function matches(node: OrgNode, term: string): boolean {
  if (!term) return true;
  const t = term.toLowerCase();
  if (
    node.name.toLowerCase().includes(t) ||
    (node.head_name ?? "").toLowerCase().includes(t) ||
    (node.officer_in_charge_name ?? "").toLowerCase().includes(t)
  ) {
    return true;
  }
  return node.children.some((c) => matches(c, term));
}

/** Keep only the branches that contain a match, so the tree stays readable. */
function prune(node: OrgNode, term: string): OrgNode {
  if (!term) return node;
  return {
    ...node,
    children: node.children.filter((c) => matches(c, term)).map((c) => prune(c, term)),
  };
}

export default function OrganizationPage() {
  // Anyone can view this page — no login required. Signed-in Admin/HR get
  // the authenticated endpoint (with clickable links into the directory);
  // an anonymous visitor gets the public one instead. Never call the
  // authenticated endpoint without a session — it would 401 and bounce an
  // anonymous visitor straight to /login.
  const { user, loading: authLoading } = useAuth();
  const signedIn = !!user;
  const treePath = authLoading
    ? null
    : signedIn
      ? "/api/org-units/tree"
      : "/api/public/org-unit-tree";

  const { data, loading } = useApi<OrgNode[]>(treePath);
  const [search, setSearch] = useState("");
  const [depth, setDepth] = useState(2);

  const roots = useMemo(() => {
    const visible = (data ?? []).filter((n) => matches(n, search));
    return visible.map((n) => prune(n, search));
  }, [data, search]);

  return (
    <>
      <SectionTitle
        title="AVFU Organisation Hierarchy"
        subtitle="The statutory university organogram, followed by the editable College → Establishment / Department → Section structure."
      />

      <div className="mb-6">
        <UniversityOrganogram />
      </div>

      <h2 className="mb-3 text-lg font-bold">Establishment &amp; Department structure</h2>

      <div className="card mb-5 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <Search
              size={19}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]"
            />
            <input
              className="input pl-11"
              placeholder="Search organisations, heads or officers-in-charge"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
            Expand
            <select
              className="input px-2 py-1.5 text-sm"
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
            >
              {DEPTH_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {authLoading || loading ? (
        <Skeleton className="h-[520px]" />
      ) : roots.length === 0 ? (
        <Empty message="No organisations match that search" />
      ) : (
        <OrgChart
          // Remount when the expansion depth or search changes so nodes re-open.
          key={`${depth}-${search}`}
          roots={roots}
          defaultDepth={search ? 9 : depth}
          linkable={signedIn}
        />
      )}

      <p className="mt-4 flex items-center gap-1.5 text-sm text-[var(--color-ink-faint)]">
        <Building2 size={15} />
        Click a branch to open or close it. Use “Office” to open a unit’s Part
        A / B / C page. Only Admin/HR can change the structure; a Department
        Head can edit within their own department.
      </p>
    </>
  );
}
