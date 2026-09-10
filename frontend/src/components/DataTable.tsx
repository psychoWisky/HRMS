"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  ChevronUp,
  Search,
} from "lucide-react";
import { Empty, Skeleton } from "./ui";

export interface Column<T> {
  header: string;
  cell: (row: T) => React.ReactNode;
  className?: string;
  /** Value used for sorting and searching this column. Omit to disable both. */
  value?: (row: T) => string | number | null | undefined;
  /** Force-disable sorting even when `value` is supplied. */
  sortable?: boolean;
}

const PAGE_SIZES = [10, 25, 50, 100];

function compare(a: unknown, b: unknown): number {
  const aEmpty = a === null || a === undefined || a === "";
  const bEmpty = b === null || b === undefined || b === "";
  if (aEmpty && bEmpty) return 0;
  // Blanks always sort last, whichever direction is active.
  if (aEmpty) return 1;
  if (bEmpty) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

export function DataTable<T extends { id: number | string }>({
  columns,
  rows,
  loading,
  empty = "Nothing to show yet",
  searchable = true,
  searchPlaceholder = "Search this table",
  pageSize: initialPageSize = 25,
  /** Extra controls rendered beside the search box (filters, buttons). */
  toolbar,
}: {
  columns: Column<T>[];
  rows: T[];
  loading?: boolean;
  empty?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  pageSize?: number;
  toolbar?: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [sortIndex, setSortIndex] = useState<number | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const canSort = (c: Column<T>) => !!c.value && c.sortable !== false;
  const hasSearchable = columns.some((c) => !!c.value);

  // Search across every column that exposes a value.
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term || !hasSearchable) return rows;
    return rows.filter((row) =>
      columns.some((c) => {
        if (!c.value) return false;
        const v = c.value(row);
        return v !== null && v !== undefined && String(v).toLowerCase().includes(term);
      })
    );
  }, [rows, query, columns, hasSearchable]);

  const sorted = useMemo(() => {
    if (sortIndex === null) return filtered;
    const col = columns[sortIndex];
    if (!col?.value) return filtered;
    const factor = sortDir === "asc" ? 1 : -1;
    // Copy first: Array.prototype.sort mutates, and `filtered` may be `rows`.
    return [...filtered].sort(
      (a, b) => compare(col.value!(a), col.value!(b)) * factor
    );
  }, [filtered, sortIndex, sortDir, columns]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * pageSize;
  const visible = sorted.slice(start, start + pageSize);

  // A new search or filter should return the reader to the first page.
  useEffect(() => {
    setPage(1);
  }, [query, pageSize, rows.length]);

  function toggleSort(index: number) {
    if (sortIndex === index) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortIndex(index);
      setSortDir("asc");
    }
  }

  const controls = (searchable && hasSearchable) || toolbar ? (
    <div className="mb-3 flex flex-wrap items-center gap-3">
      {searchable && hasSearchable && (
        <div className="relative min-w-[240px] flex-1">
          <Search
            size={18}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]"
          />
          <input
            className="input py-2.5 pl-11"
            placeholder={searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={searchPlaceholder}
          />
        </div>
      )}
      {toolbar}
    </div>
  ) : null;

  if (loading) {
    return (
      <div>
        {controls}
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      {controls}

      {sorted.length === 0 ? (
        <Empty
          message={
            query.trim() ? `No rows match “${query.trim()}”` : empty
          }
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-2xl border border-[var(--color-line)]">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr
                  className="text-sm font-semibold text-white"
                  style={{
                    background:
                      "linear-gradient(180deg, var(--color-green-soft), var(--color-green))",
                  }}
                >
                  {columns.map((c, i) => {
                    const sortable = canSort(c);
                    const active = sortIndex === i;
                    return (
                      <th
                        key={i}
                        className={`px-4 py-3.5 ${c.className ?? ""}`}
                        aria-sort={
                          active
                            ? sortDir === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                      >
                        {sortable ? (
                          <button
                            onClick={() => toggleSort(i)}
                            className="inline-flex items-center gap-1.5 font-semibold transition-opacity hover:opacity-80"
                            title={`Sort by ${c.header}`}
                          >
                            {c.header}
                            {active ? (
                              sortDir === "asc" ? (
                                <ChevronUp size={15} />
                              ) : (
                                <ChevronDown size={15} />
                              )
                            ) : (
                              <ChevronsUpDown size={15} className="opacity-50" />
                            )}
                          </button>
                        ) : (
                          c.header
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => (
                  <tr
                    key={row.id}
                    className="border-t border-[var(--color-line)] bg-white text-[15px] transition-colors hover:bg-[var(--color-bg)]"
                  >
                    {columns.map((c, ci) => (
                      <td key={ci} className={`px-4 py-3.5 ${c.className ?? ""}`}>
                        {c.cell(row)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm text-[var(--color-ink-soft)]">
            <span>
              Showing <strong>{start + 1}</strong>–
              <strong>{Math.min(start + pageSize, sorted.length)}</strong> of{" "}
              <strong>{sorted.length}</strong>
              {sorted.length !== rows.length && ` (filtered from ${rows.length})`}
            </span>

            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2">
                Rows
                <select
                  className="input px-2 py-1.5 text-sm"
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  aria-label="Rows per page"
                >
                  {PAGE_SIZES.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="rounded-lg border border-[var(--color-line)] bg-white p-1.5 disabled:opacity-40"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={17} />
                </button>
                <span className="px-2">
                  Page <strong>{currentPage}</strong> of{" "}
                  <strong>{totalPages}</strong>
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="rounded-lg border border-[var(--color-line)] bg-white p-1.5 disabled:opacity-40"
                  aria-label="Next page"
                >
                  <ChevronRight size={17} />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
