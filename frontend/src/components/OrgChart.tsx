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
          expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />
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
            <Link href={`/manage/org-units/${node.id}`} className="org-row-staff">
              Office
            </Link>
          )}
          <Link href={`/directory?org_unit_id=${node.id}`} className="org-row-staff">
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
        onToggle={() => setOpen((value) => !value)}
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

export function OrgChart({
  roots,
  defaultDepth = 2,
  linkable = true,
}: {
  roots: OrgNode[];
  defaultDepth?: number;
  linkable?: boolean;
}) {
  return (
    <div className="org-tree">
      <ul>
        {roots.map((root) => (
          <Branch
            key={root.id}
            node={root}
            depth={0}
            defaultDepth={defaultDepth}
            linkable={linkable}
          />
        ))}
      </ul>
    </div>
  );
}
