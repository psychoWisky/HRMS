"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";

export interface SelectOption {
  value: string;
  label: string;
}

export function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = "Select...",
  searchPlaceholder = "Search options...",
  disabled = false,
  className = "",
}: {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const selected = options.find((option) => option.value === value);
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return term
      ? options.filter((option) => option.label.toLowerCase().includes(term))
      : options;
  }, [options, query]);

  useEffect(() => {
    function close(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    if (open) requestAnimationFrame(() => searchRef.current?.focus());
  }, [open]);

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          setOpen((current) => !current);
          setQuery("");
        }}
        className="input flex w-full items-center justify-between gap-2 py-2.5 text-left disabled:cursor-not-allowed disabled:opacity-60"
      >
        <span className={`truncate ${selected ? "" : "text-[var(--color-ink-faint)]"}`}>
          {selected?.label ?? placeholder}
        </span>
        <ChevronDown size={16} className={`shrink-0 text-[var(--color-ink-faint)] ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-[100] mt-1.5 w-full min-w-[240px] overflow-hidden rounded-xl border bg-[var(--color-surface)] shadow-xl" style={{ borderColor: "var(--color-line)" }}>
          <div className="relative border-b border-[var(--color-line)] p-2">
            <Search size={15} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)]" />
            <input
              ref={searchRef}
              className="input py-1.5 pl-8 pr-8 text-sm"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={searchPlaceholder}
            />
            {query && <X size={14} className="absolute right-4 top-1/2 -translate-y-1/2 cursor-pointer text-[var(--color-ink-faint)]" onClick={() => setQuery("")} />}
          </div>
          <div className="max-h-64 overflow-y-auto py-1">
            {value && (
              <button type="button" className="w-full px-4 py-2 text-left text-sm text-[var(--color-ink-faint)] hover:bg-[var(--color-surface-2)]" onClick={() => { onChange(""); setOpen(false); }}>
                {placeholder}
              </button>
            )}
            {filtered.length === 0 ? <p className="px-4 py-5 text-center text-sm text-[var(--color-ink-faint)]">No match</p> : filtered.map((option) => (
              <button key={option.value} type="button" className={`flex w-full items-center justify-between gap-2 px-4 py-2 text-left text-sm hover:bg-[var(--color-green-tint)] ${option.value === value ? "bg-[var(--color-green-tint)] font-semibold text-[var(--color-green)]" : ""}`} onClick={() => { onChange(option.value); setOpen(false); }}>
                <span className="truncate">{option.label}</span>
                {option.value === value && <Check size={15} />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
