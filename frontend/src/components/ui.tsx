"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Inbox } from "lucide-react";
import { getToken } from "@/lib/api";
import { initials } from "@/lib/format";

/* ---------------- Status badge (green / black / white, boxy) ---------------- */
const STATUS_STYLE: Record<string, string> = {
  approved: "bg-[#e6efe9] text-[#14532d] border-[#bcd3c4]",
  sanctioned: "bg-[#e6efe9] text-[#14532d] border-[#bcd3c4]",
  present: "bg-[#e6efe9] text-[#14532d] border-[#bcd3c4]",
  working: "bg-[#e6efe9] text-[#14532d] border-[#bcd3c4]",
  active: "bg-[#e6efe9] text-[#14532d] border-[#bcd3c4]",
  pending: "bg-[#f4f1e4] text-[#6b5510] border-[#ddd2af]",
  rejected: "bg-[#f6ebeb] text-[#8a1c1c] border-[#e0c4c4]",
  cancelled: "bg-[#eef0ef] text-[#41504a] border-[#d4ddd8]",
};

export function StatusBadge({
  status,
  label,
}: {
  /** Drives the colour; use `label` when the display text differs. */
  status: string;
  label?: string;
}) {
  const cls =
    STATUS_STYLE[status.toLowerCase()] ?? "bg-[#eef0ef] text-[#41504a] border-[#d4ddd8]";
  const text = label ?? status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <span className={`badge ${cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {text}
    </span>
  );
}

/** Small label/value pair used across profile and detail screens. */
export function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
        {label}
      </p>
      <p
        className={`mt-1 text-[15px] text-[var(--color-ink)] ${
          mono ? "font-mono" : ""
        }`}
      >
        {value || "—"}
      </p>
    </div>
  );
}

/** Headline number tile for dashboards. */
export function StatTile({
  label,
  value,
  hint,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon?: React.ComponentType<{ size?: number }>;
  tone?: "default" | "warn" | "danger";
}) {
  const color =
    tone === "danger"
      ? "var(--color-danger)"
      : tone === "warn"
        ? "var(--color-warn)"
        : "var(--color-green)";
  return (
    <div className="card p-5">
      {Icon && (
        <span style={{ color }} className="inline-flex">
          <Icon size={22} />
        </span>
      )}
      <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
        {label}
      </p>
      <p className="mt-1 text-3xl font-bold" style={{ color }}>
        {value}
      </p>
      {hint && (
        <p className="mt-1 text-xs text-[var(--color-ink-faint)]">{hint}</p>
      )}
    </div>
  );
}

/* ---------------- Avatar ---------------- */
/** Fetches an authenticated (Bearer-token) image into a local object URL,
 *  since a plain `<img src>` cannot attach an Authorization header. */
function useAuthImage(src?: string | null): string | null {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!src) {
      setObjectUrl(null);
      return;
    }
    let revoked = "";
    const token = getToken();
    fetch(src, token ? { headers: { Authorization: `Bearer ${token}` } } : {})
      .then((res) => (res.ok ? res.blob() : Promise.reject()))
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        revoked = url;
        setObjectUrl(url);
      })
      .catch(() => setObjectUrl(null));
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [src]);

  return objectUrl;
}

export function Avatar({
  name,
  src,
  size = 44,
}: {
  name: string;
  /** Employee photo URL (an authenticated `/api/.../photo/...` endpoint). */
  src?: string | null;
  size?: number;
}) {
  const objectUrl = useAuthImage(src);
  if (objectUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- object URL,
      // not a remote asset next/image's allowlist would apply to.
      <img
        src={objectUrl}
        alt={name}
        className="shrink-0 rounded-full object-cover"
        style={{
          width: size,
          height: size,
          boxShadow: "inset 0 0 0 2px rgba(255,255,255,0.15)",
        }}
      />
    );
  }
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        background:
          "linear-gradient(135deg, var(--color-green-soft), var(--color-green-deep))",
        boxShadow: "inset 0 0 0 2px rgba(255,255,255,0.15)",
      }}
    >
      {initials(name) || "?"}
    </div>
  );
}

/* ---------------- Animated card ---------------- */
export function MotionCard({
  children,
  className = "",
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -2, boxShadow: "var(--shadow-md)" }}
      className={`card p-6 ${className}`}
    >
      {children}
    </motion.div>
  );
}

/* ---------------- Section header ---------------- */
export function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3">
        <span className="accent-bar" />
        <h1 className="text-3xl font-bold text-[var(--color-ink)]">{title}</h1>
      </div>
      {subtitle && (
        <p className="mt-2 pl-[17px] text-[var(--color-ink-soft)]">{subtitle}</p>
      )}
    </div>
  );
}

/* ---------------- Empty state ---------------- */
export function Empty({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <div
        className="flex h-14 w-14 items-center justify-center border-2 text-[var(--color-green)]"
        style={{ borderColor: "var(--color-line-strong)", borderRadius: "var(--radius)" }}
      >
        <Inbox size={26} />
      </div>
      <p className="text-[var(--color-ink-faint)]">{message}</p>
    </div>
  );
}

/* ---------------- Loading skeleton ---------------- */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`shimmer border border-[var(--color-line)] ${className}`}
      style={{ borderRadius: "var(--radius)" }}
    />
  );
}

/* ---------------- Spinner ---------------- */
export function Spinner({ size = 22 }: { size?: number }) {
  return (
    <span
      className="inline-block animate-spin rounded-full border-2 border-current border-t-transparent"
      style={{ width: size, height: size }}
    />
  );
}
