"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search, X } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { orgUnitLabel } from "@/lib/format";

interface Unit {
  id: number;
  kind: string;
  sub_kind: string;
  name: string;
  path: string;
  is_active: boolean;
}

const GROUP_ORDER = ["university", "college", "establishment", "department", "section"];
const GROUP_TITLE: Record<string, string> = {
  university: "University",
  college: "Colleges",
  establishment: "Establishments",
  department: "Departments",
  section: "Sections / Units / Cells",
};

/**
 * A searchable, grouped dropdown over the AVFU org-unit tree — Colleges,
 * Establishments, Departments and Sections/Units/Cells shown as distinct
 * groups (never flattened into one "organisation" list), with a search box
 * inside the panel to filter by name or path.
 */
export function OrgUnitSelect({
  value,
  onChange,
  placeholder = "All establishments / departments",
  allowClear = true,
  className = "",
}: {
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
  allowClear?: boolean;
  className?: string;
}) {
  const { data } = useApi<Unit[]>("/api/org-units?limit=1000");
  const units = useMemo(() => (data ?? []).filter((u) => u.is_active), [data]);
  const byId = useMemo(() => new Map(units.map((u) => [u.id, u])), [units]);

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      requestAnimationFrame(() => searchRef.current?.focus());
    }
  }, [open]);

  const grouped = useMemo(() => {
    const term = query.trim().toLowerCase();
    const filtered = term
      ? units.filter(
          (u) =>
            u.name.toLowerCase().includes(term) ||
            u.path.toLowerCase().includes(term)
        )
      : units;
    const byKind = new Map<string, Unit[]>();
    for (const u of filtered) {
      const list = byKind.get(u.kind) ?? [];
      list.push(u);
      byKind.set(u.kind, list);
    }
    for (const list of byKind.values()) {
      list.sort((a, b) => a.path.localeCompare(b.path));
    }
    return GROUP_ORDER.filter((k) => byKind.has(k)).map((k) => ({
      kind: k,
      title: GROUP_TITLE[k],
      items: byKind.get(k)!,
    }));
  }, [units, query]);

  const selected = value ? byId.get(value) : null;

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="input flex w-full items-center justify-between gap-2 py-2.5 text-left"
      >
        <span
          className={`truncate ${
            selected ? "" : "text-[var(--color-ink-faint)]"
          }`}
        >
          {selected ? selected.path : placeholder}
        </span>
        <span className="flex shrink-0 items-center gap-1">
          {selected && allowClear && (
            <X
              size={15}
              className="text-[var(--color-ink-faint)] hover:text-[var(--color-danger)]"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
            />
          )}
          <ChevronDown
            size={15}
            className={`text-[var(--color-ink-faint)] transition-transform ${
              open ? "rotate-180" : ""
            }`}
          />
        </span>
      </button>

      {open && (
        <div
          className="absolute z-30 mt-1.5 w-max min-w-full max-w-[min(32rem,90vw)] overflow-hidden rounded-xl border bg-[var(--color-surface)]"
          style={{
            borderColor: "var(--color-line)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          <div className="relative border-b border-[var(--color-line)] p-2">
            <Search
              size={15}
              className="pointer-events-none absolute left-4.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]"
            />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search establishments, departments, sections…"
              className="input py-1.5 pl-8 text-sm"
            />
          </div>

          <div className="max-h-72 overflow-y-auto py-1">
            {allowClear && !query && (
              <button
                type="button"
                onClick={() => {
                  onChange(null);
                  setOpen(false);
                }}
                className="block w-full px-4 py-2 text-left text-sm text-[var(--color-ink-faint)] hover:bg-[var(--color-surface-2)]"
              >
                {placeholder}
              </button>
            )}
            {grouped.length === 0 && (
              <p className="px-4 py-6 text-center text-sm text-[var(--color-ink-faint)]">
                No match
              </p>
            )}
            {grouped.map((group) => (
              <div key={group.kind}>
                <p className="px-4 pb-1 pt-2.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                  {group.title}
                </p>
                {group.items.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => {
                      onChange(u.id);
                      setOpen(false);
                    }}
                    className={`block w-full whitespace-normal break-words px-4 py-2 text-left text-sm leading-snug hover:bg-[var(--color-green-tint)] ${
                      value === u.id
                        ? "bg-[var(--color-green-tint)] font-semibold text-[var(--color-green)]"
                        : ""
                    }`}
                    title={u.path}
                  >
                    {u.name}
                    {u.kind === "section" && u.sub_kind && (
                      <span className="ml-1.5 text-xs text-[var(--color-ink-faint)]">
                        ({orgUnitLabel("section", u.sub_kind)})
                      </span>
                    )}
                    {u.path !== u.name && (
                      <span className="block text-xs text-[var(--color-ink-faint)]">
                        {u.path}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
