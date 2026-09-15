"use client";

import { useState } from "react";
import { Pencil, Plus, Power } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { titleize } from "@/lib/format";
import { SectionTitle, Spinner, StatusBadge } from "@/components/ui";

interface Designation {
  id: number;
  name: string;
  short_name: string;
  category: string;
  rank_level: number;
  description: string;
  is_active: boolean;
  sanctioned_total: number;
  occupied_total: number;
  vacant_total: number;
}

const CATEGORIES = [
  "officer",
  "teaching",
  "scientific",
  "administrative",
  "accounts",
  "technical",
  "support",
];

const BLANK = {
  name: "",
  short_name: "",
  category: "administrative",
  rank_level: "50",
  description: "",
};

export default function ManageDesignationsPage() {
  const { can } = useAuth();
  const { push } = useToast();
  // Every designation loads at once; the table handles search and paging.
  const { data, loading, reload } = useApi<Designation[]>(
    "/api/designations?include_inactive=true"
  );
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Designation | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [busy, setBusy] = useState(false);

  const canManage = can(P.designationManage);

  async function save() {
    setBusy(true);
    const payload = {
      name: form.name,
      short_name: form.short_name,
      category: form.category,
      rank_level: Number(form.rank_level) || 50,
      description: form.description,
    };
    try {
      if (editing) {
        await api.put(`/api/designations/${editing.id}`, payload);
        push("success", "Designation updated");
      } else {
        await api.post("/api/designations", payload);
        push("success", "Designation created");
      }
      setOpen(false);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function deactivate(row: Designation) {
    try {
      await api.del(`/api/designations/${row.id}`);
      push("success", `${row.name} deactivated`);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  const columns: Column<Designation>[] = [
    {
      header: "Designation",
      value: (r) => `${r.name} ${r.short_name}`,
      cell: (r) => (
        <div>
          <p className="font-semibold">{r.name}</p>
          {r.short_name && (
            <p className="text-xs text-[var(--color-ink-faint)]">{r.short_name}</p>
          )}
        </div>
      ),
    },
    {
      header: "Category",
      value: (r) => r.category,
      cell: (r) => titleize(r.category),
    },
    { header: "Rank", value: (r) => r.rank_level, cell: (r) => r.rank_level },
    {
      header: "Sanctioned",
      value: (r) => r.sanctioned_total,
      cell: (r) => r.sanctioned_total,
    },
    {
      header: "Occupied",
      value: (r) => r.occupied_total,
      cell: (r) => r.occupied_total,
    },
    {
      header: "Vacant",
      value: (r) => r.vacant_total,
      cell: (r) => (
        <span
          style={{
            color: r.vacant_total > 0 ? "var(--color-warn)" : "inherit",
            fontWeight: r.vacant_total > 0 ? 600 : 400,
          }}
        >
          {r.vacant_total}
        </span>
      ),
    },
    {
      header: "Status",
      value: (r) => (r.is_active ? "Active" : "Inactive"),
      cell: (r) => (
        <StatusBadge
          status={r.is_active ? "active" : "cancelled"}
          label={r.is_active ? "Active" : "Inactive"}
        />
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
                  name: r.name,
                  short_name: r.short_name,
                  category: r.category,
                  rank_level: String(r.rank_level),
                  description: r.description,
                });
                setOpen(true);
              }}
              className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
              title="Edit"
            >
              <Pencil size={15} /> <span>Edit</span>
            </button>
            {r.is_active && (
              <button
                onClick={() => deactivate(r)}
                className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-danger)] hover:bg-[#fbf0f0]"
                title="Deactivate"
              >
                <Power size={15} /> <span>Deactivate</span>
              </button>
            )}
          </div>
        ) : null,
    },
  ];

  return (
    <>
      <div className="mb-2 flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          title="Designations"
          subtitle="Every designation in the university, with its sanctioned strength and current vacancy across all offices."
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
            <Plus size={18} /> Add designation
          </button>
        )}
      </div>

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No designations recorded"
        searchPlaceholder="Search designation, short name or category"
      />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? `Edit ${editing.name}` : "Add designation"}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="label">Name *</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Short name</label>
            <input
              className="input"
              value={form.short_name}
              onChange={(e) => setForm({ ...form, short_name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Category</label>
            <select
              className="input"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {titleize(c)}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="label">Rank level</label>
            <input
              className="input"
              type="number"
              value={form.rank_level}
              onChange={(e) => setForm({ ...form, rank_level: e.target.value })}
            />
            <p className="mt-1 text-xs text-[var(--color-ink-faint)]">
              Lower is more senior. Vice-Chancellor is 2; support staff are 28–30.
            </p>
          </div>
          <div className="sm:col-span-2">
            <label className="label">Description</label>
            <textarea
              className="input min-h-20"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
        </div>
        <button
          onClick={save}
          className="btn btn-primary mt-4 w-full"
          disabled={busy || !form.name}
        >
          {busy ? <Spinner /> : editing ? "Save changes" : "Create designation"}
        </button>
      </Modal>
    </>
  );
}
