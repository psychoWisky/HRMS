"use client";

import { useMemo, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { SectionTitle, Spinner, StatTile } from "@/components/ui";

interface Post {
  id: number;
  org_unit_id: number;
  org_unit_name: string;
  level_no: number;
  designation_id: number;
  designation_name: string;
  sanctioned_count: number;
  occupied_count: number;
  vacant_count: number;
  over_strength_count: number;
  reported_vacant_count: number;
  reports_to_note: string;
  remarks: string;
}

interface Option {
  id: number;
  name: string;
}

const BLANK = {
  org_unit_id: "",
  designation_id: "",
  sanctioned_count: "1",
  reported_vacant_count: "0",
  level_no: "0",
  reports_to_note: "",
  remarks: "",
};

export default function ManagePostsPage() {
  const { can } = useAuth();
  const { push } = useToast();

  const [orgId, setOrgId] = useState("");
  const [vacantOnly, setVacantOnly] = useState(false);

  const path = useMemo(() => {
    const params = new URLSearchParams();
    if (orgId) params.set("org_unit_id", orgId);
    if (vacantOnly) params.set("vacant_only", "true");
    return `/api/posts?${params.toString()}`;
  }, [orgId, vacantOnly]);

  const { data, loading, reload } = useApi<Post[]>(path);
  const { data: orgs } = useApi<Option[]>("/api/org-units");
  const { data: designations } = useApi<Option[]>("/api/designations");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Post | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [busy, setBusy] = useState(false);

  const canManage = can(P.postManage);
  const rows = data ?? [];

  const totals = rows.reduce(
    (acc, r) => ({
      sanctioned: acc.sanctioned + r.sanctioned_count,
      occupied: acc.occupied + r.occupied_count,
      vacant: acc.vacant + r.vacant_count,
    }),
    { sanctioned: 0, occupied: 0, vacant: 0 }
  );

  async function save() {
    setBusy(true);
    const payload = {
      org_unit_id: Number(form.org_unit_id),
      designation_id: Number(form.designation_id),
      sanctioned_count: Number(form.sanctioned_count) || 0,
      reported_vacant_count: Number(form.reported_vacant_count) || 0,
      level_no: Number(form.level_no) || 0,
      reports_to_note: form.reports_to_note,
      remarks: form.remarks,
    };
    try {
      if (editing) {
        await api.put(`/api/posts/${editing.id}`, payload);
        push("success", "Post updated");
      } else {
        await api.post("/api/posts", payload);
        push("success", "Sanctioned post created");
      }
      setOpen(false);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(row: Post) {
    try {
      await api.del(`/api/posts/${row.id}`);
      push("success", "Post deleted");
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Delete failed");
    }
  }

  const columns: Column<Post>[] = [
    {
      header: "Organisation",
      value: (r) => r.org_unit_name,
      cell: (r) => <span className="text-sm">{r.org_unit_name}</span>,
    },
    {
      header: "Designation",
      value: (r) => r.designation_name,
      cell: (r) => <span className="font-semibold">{r.designation_name}</span>,
    },
    {
      header: "Level",
      value: (r) => r.level_no,
      cell: (r) => r.level_no || "—",
    },
    {
      header: "Reports to",
      value: (r) => r.reports_to_note,
      cell: (r) => (
        <span className="text-sm text-[var(--color-ink-soft)]">
          {r.reports_to_note || "—"}
        </span>
      ),
    },
    {
      header: "Sanctioned",
      value: (r) => r.sanctioned_count,
      cell: (r) => r.sanctioned_count,
    },
    {
      header: "Occupied",
      value: (r) => r.occupied_count,
      cell: (r) => (
        <span>
          {r.occupied_count}
          {r.over_strength_count > 0 && (
            <span
              className="ml-1.5 rounded px-1.5 py-0.5 text-xs font-semibold"
              style={{ background: "#fdf6e3", color: "var(--color-warn)" }}
              title="More employees in post than the sanctioned strength"
            >
              +{r.over_strength_count} over
            </span>
          )}
        </span>
      ),
    },
    {
      header: "Vacant",
      value: (r) => r.vacant_count,
      cell: (r) => (
        <span
          style={{
            color: r.vacant_count > 0 ? "var(--color-warn)" : "inherit",
            fontWeight: r.vacant_count > 0 ? 600 : 400,
          }}
        >
          {r.vacant_count}
        </span>
      ),
    },
    {
      header: "Remarks",
      value: (r) => r.remarks,
      cell: (r) => (
        <span className="text-xs text-[var(--color-ink-faint)]">
          {r.remarks || "—"}
        </span>
      ),
    },
    {
      header: "",
      cell: (r) =>
        canManage ? (
          <div className="flex gap-1.5">
            <button
              onClick={() => {
                setEditing(r);
                setForm({
                  org_unit_id: String(r.org_unit_id),
                  designation_id: String(r.designation_id),
                  sanctioned_count: String(r.sanctioned_count),
                  reported_vacant_count: String(r.reported_vacant_count),
                  level_no: String(r.level_no ?? 0),
                  reports_to_note: r.reports_to_note,
                  remarks: r.remarks,
                });
                setOpen(true);
              }}
              className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
              title="Edit"
            >
              <Pencil size={16} />
            </button>
            <button
              onClick={() => remove(r)}
              className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-danger)] hover:bg-[#fbf0f0]"
              title="Delete"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ) : null,
    },
  ];

  return (
    <>
      <div className="mb-2 flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          title="Posts & Vacancies"
          subtitle="Sanctioned strength per office and designation. Vacancy is calculated as sanctioned minus employees actually holding the post."
        />
        {canManage && (
          <button
            onClick={() => {
              setEditing(null);
              setForm({ ...BLANK });
              setOpen(true);
            }}
            className="btn btn-primary"
          >
            <Plus size={18} /> Add sanctioned post
          </button>
        )}
      </div>

      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <StatTile label="Sanctioned" value={totals.sanctioned} />
        <StatTile label="Occupied" value={totals.occupied} />
        <StatTile label="Vacant" value={totals.vacant} tone="warn" />
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        loading={loading}
        empty="No sanctioned posts match those filters"
        searchPlaceholder="Search office, designation, reporting line or remarks"
        toolbar={
          <>
            <select
              className="input w-auto min-w-[220px] py-2.5"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
            >
              <option value="">All organisations (whole university)</option>
              {(orgs ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-[var(--color-ink-soft)]">
              <input
                type="checkbox"
                checked={vacantOnly}
                onChange={(e) => setVacantOnly(e.target.checked)}
              />
              Vacant posts only
            </label>
          </>
        }
      />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? "Edit sanctioned post" : "Add sanctioned post"}
        wide
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Office / org unit *</label>
            <select
              className="input"
              value={form.org_unit_id}
              onChange={(e) =>
                setForm({ ...form, org_unit_id: e.target.value })
              }
              disabled={!!editing}
            >
              <option value="">Select…</option>
              {(orgs ?? []).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Designation *</label>
            <select
              className="input"
              value={form.designation_id}
              onChange={(e) =>
                setForm({ ...form, designation_id: e.target.value })
              }
              disabled={!!editing}
            >
              <option value="">Select…</option>
              {(designations ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Sanctioned posts *</label>
            <input
              className="input"
              type="number"
              min={0}
              value={form.sanctioned_count}
              onChange={(e) =>
                setForm({ ...form, sanctioned_count: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label">Vacancy reported by the office</label>
            <input
              className="input"
              type="number"
              min={0}
              value={form.reported_vacant_count}
              onChange={(e) =>
                setForm({ ...form, reported_vacant_count: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label">Level № (Part B order)</label>
            <input
              className="input"
              type="number"
              value={form.level_no}
              onChange={(e) => setForm({ ...form, level_no: e.target.value })}
              placeholder="e.g. 2"
            />
          </div>
          <div>
            <label className="label">Reports to (as recorded)</label>
            <input
              className="input"
              value={form.reports_to_note}
              onChange={(e) =>
                setForm({ ...form, reports_to_note: e.target.value })
              }
              placeholder="e.g. HOD / Dean / Registrar"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Remarks</label>
            <input
              className="input"
              value={form.remarks}
              onChange={(e) => setForm({ ...form, remarks: e.target.value })}
            />
          </div>
        </div>
        <button
          onClick={save}
          className="btn btn-primary mt-4 w-full"
          disabled={busy || !form.org_unit_id || !form.designation_id}
        >
          {busy ? <Spinner /> : editing ? "Save changes" : "Create post"}
        </button>
      </Modal>
    </>
  );
}
