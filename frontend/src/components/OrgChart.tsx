"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  ChevronDown,
  ChevronRight,
  MapPin,
  UserCircle2,
  Users,
} from "lucide-react";
import { orgUnitLabel } from "@/lib/format";

export interface OrgNode {
  id: number;
  name: string;
  short_code: string;
  kind: string;
  sub_kind?: string;
  location_name: string | null;
  head_name: string | null;
  head_id: number | null;
  officer_in_charge_name: string | null;
  direct_employee_count: number;
  total_employee_count: number;
  sanctioned_count: number;
  children: OrgNode[];
}

/** Left accent colour by kind, so depth reads at a glance without heavy boxes. */
const TIER_ACCENT: Record<string, string> = {
  college: "var(--color-green-deep)",
  establishment: "var(--color-green)",
  department: "var(--color-green-soft)",
  section: "var(--color-line-strong)",
};

function Row({
  node,
  depth,
  expanded,
  onToggle,
  linkable,
}: {
  node: OrgNode;
  depth: number;
  expanded: boolean;
  onToggle: () => void;
  /** Link head names and "Staff" through to the employee directory.
   *  False for anonymous visitors, since the directory itself requires
   *  an Admin/HR login — a dead link would be worse than plain text. */
  linkable: boolean;
}) {
  const hasChildren = node.children.length > 0;
  const accent = TIER_ACCENT[node.kind] ?? TIER_ACCENT.section;
  const isTop = depth === 0;

  return (
    <div
      className="org-row"
      style={{ borderLeftColor: accent }}
      data-top={isTop || undefined}
    >
      <button
        onClick={onToggle}
        disabled={!hasChildren}
        aria-label={expanded ? "Collapse" : "Expand"}
        className="org-row-toggle"
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown size={16} />
          ) : (
            <ChevronRight size={16} />
          )
        ) : (
          <span className="org-row-dot" />
        )}
      </button>

      <div className="min-w-0 flex-1 py-2 pr-3">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className={isTop ? "text-lg font-bold" : "font-semibold"}>
            {node.name}
          </span>
          <span className="org-type-badge">
            {orgUnitLabel(node.kind, node.sub_kind)}
          </span>
          {node.short_code && (
            <span className="text-xs font-mono text-[var(--color-ink-faint)]">
              {node.short_code}
            </span>
          )}
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-[var(--color-ink-faint)]">
          {(node.head_name || node.officer_in_charge_name) && (
            <span className="flex items-center gap-1.5">
              <UserCircle2 size={14} />
              {!node.head_name && <span className="text-xs">Officer-in-charge:</span>}
              {linkable && node.head_id ? (
                <Link
                  href={`/directory/${node.head_id}`}
                  className="font-medium text-[var(--color-green)] hover:underline"
                >
                  {node.head_name}
                </Link>
              ) : (
                <span className="font-medium text-[var(--color-ink-soft)]">
                  {node.head_name ?? node.officer_in_charge_name}
                </span>
              )}
            </span>
          )}
          {node.location_name && (
            <span className="flex items-center gap-1.5">
              <MapPin size={14} /> {node.location_name}
            </span>
          )}
          <span className="flex items-center gap-1.5">
            <Users size={14} /> {node.total_employee_count} employee
            {node.total_employee_count === 1 ? "" : "s"}
          </span>
          {node.sanctioned_count > 0 && (
            <span className="flex items-center gap-1.5">
              <Briefcase size={14} /> {node.sanctioned_count} sanctioned posts
            </span>
          )}
        </div>
      </div>

      {linkable && (
        <div className="flex shrink-0 items-center gap-2 pr-1">
          {node.kind !== "college" && (
            <Link
              href={`/manage/org-units/${node.id}`}
              className="org-row-staff"
            >
              Office
            </Link>
          )}
          <Link
            href={`/directory?org_unit_id=${node.id}`}
            className="org-row-staff"
          >
            Staff
          </Link>
        </div>
      )}
    </div>
  );
}

function Branch({
  node,
  depth,
  defaultDepth,
  linkable,
}: {
  node: OrgNode;
  depth: number;
  defaultDepth: number;
  linkable: boolean;
}) {
  const [open, setOpen] = useState(depth < defaultDepth);
  const hasChildren = node.children.length > 0;

  return (
    <li>
      <Row
        node={node}
        depth={depth}
        expanded={open}
        onToggle={() => setOpen((o) => !o)}
        linkable={linkable}
      />
      {hasChildren && open && (
        <ul className="org-children">
          {node.children.map((child) => (
            <Branch
              key={child.id}
              node={child}
              depth={depth + 1}
              defaultDepth={defaultDepth}
              linkable={linkable}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * A vertical, column-stacked organisation tree.
 *
 * Every level nests directly under its parent (no side-by-side boxes, no
 * horizontal scrolling) — the same reading order as a file-explorer tree,
 * which stays legible at any depth or window width.
 */
export function OrgChart({
  roots,
  defaultDepth = 2,
  linkable = true,
}: {
  roots: OrgNode[];
  /** Levels expanded on first render. */
  defaultDepth?: number;
  /** Link head names and offices through to the (login-only) directory. */
  linkable?: boolean;
}) {
  return (
    <div className="org-tree">
      <ul>
        {roots.map((r) => (
          <Branch
            key={r.id}
            node={r}
            depth={0}
            defaultDepth={defaultDepth}
            linkable={linkable}
          />
        ))}
      </ul>
    </div>
  );
}
