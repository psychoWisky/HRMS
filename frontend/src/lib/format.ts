export function fmtDate(d?: string | null): string {
  if (!d) return "—";
  const date = new Date(d);
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function fmtDateTime(d?: string | null): string {
  if (!d) return "—";
  const date = new Date(d);
  if (isNaN(date.getTime())) return "—";
  return `${fmtDate(d)}, ${date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

const HONORIFICS = new Set(["dr", "mr", "mrs", "ms", "sri", "smt", "prof"]);

export function initials(name: string): string {
  const words = name
    .split(/[\s.]+/)
    .filter(Boolean)
    .filter((w) => !HONORIFICS.has(w.toLowerCase().replace(/\./g, "")));
  return words
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");
}

/** "resubmission_required" -> "Resubmission Required" */
export function titleize(value?: string | null): string {
  if (!value) return "—";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export const ORG_TYPE_LABEL: Record<string, string> = {
  university: "University",
  campus: "Campus",
  faculty: "Faculty",
  directorate: "Directorate",
  college: "College",
  research_station: "Research Station",
  office: "Office",
  department: "Department",
  section: "Section",
  unit: "Unit",
  cell: "Cell",
};

/** OrgUnit kind + sub_kind -> label. */
export const ORG_UNIT_KIND_LABEL: Record<string, string> = {
  university: "University",
  college: "College",
  establishment: "Establishment",
  department: "Department",
  section: "Section",
  unit: "Unit",
  cell: "Cell",
};

export function orgUnitLabel(kind: string, subKind?: string | null): string {
  if (kind === "section" && subKind && ORG_UNIT_KIND_LABEL[subKind]) {
    return ORG_UNIT_KIND_LABEL[subKind];
  }
  return ORG_UNIT_KIND_LABEL[kind] ?? kind;
}

export const KYC_LABEL: Record<string, string> = {
  not_started: "Not Started",
  draft: "Draft",
  submitted: "Submitted",
  under_verification: "Under Verification",
  verified: "Verified",
  rejected: "Rejected",
  resubmission_required: "Resubmission Required",
};

/** Maps a KYC status onto the StatusBadge palette. */
export function kycTone(status?: string | null): string {
  switch (status) {
    case "verified":
      return "approved";
    case "rejected":
      return "rejected";
    case "submitted":
    case "under_verification":
    case "resubmission_required":
      return "pending";
    default:
      return "cancelled";
  }
}
