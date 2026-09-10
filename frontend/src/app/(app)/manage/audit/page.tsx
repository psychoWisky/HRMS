"use client";

import { useApi } from "@/lib/useApi";
import { Column, DataTable } from "@/components/DataTable";
import { fmtDateTime } from "@/lib/format";
import { SectionTitle } from "@/components/ui";

interface AuditRow {
  id: number;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  ip_address: string;
  created_at: string;
}

export default function AuditLogPage() {
  const { data, loading } = useApi<AuditRow[]>(
    "/api/admin/audit-logs?limit=500"
  );

  const columns: Column<AuditRow>[] = [
    {
      header: "When",
      value: (r) => r.created_at,
      cell: (r) => (
        <span className="whitespace-nowrap text-sm">
          {fmtDateTime(r.created_at)}
        </span>
      ),
    },
    {
      header: "Action",
      value: (r) => r.action,
      cell: (r) => <span className="font-mono text-xs">{r.action}</span>,
    },
    {
      header: "Actor",
      value: (r) => r.actor_email || "system",
      cell: (r) => r.actor_email || "system",
    },
    {
      header: "Entity",
      value: (r) => r.entity_type,
      cell: (r) => (
        <span className="text-sm text-[var(--color-ink-soft)]">
          {r.entity_type ? `${r.entity_type} #${r.entity_id}` : "—"}
        </span>
      ),
    },
    { header: "Summary", value: (r) => r.summary, cell: (r) => r.summary },
    {
      header: "IP",
      value: (r) => r.ip_address,
      cell: (r) => (
        <span className="font-mono text-xs text-[var(--color-ink-faint)]">
          {r.ip_address || "—"}
        </span>
      ),
    },
  ];

  return (
    <>
      <SectionTitle
        title="Audit Logs"
        subtitle="Every change to official HRMS data, with who made it and when."
      />

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No audit entries match those filters"
        searchPlaceholder="Search action, actor, entity or summary"
        pageSize={50}
      />
    </>
  );
}
