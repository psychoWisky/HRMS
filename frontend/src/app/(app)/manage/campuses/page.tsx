"use client";

import { useState } from "react";
import { MapPin, Pencil, Plus } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { SectionTitle, Spinner, StatusBadge } from "@/components/ui";

interface Location {
  id: number;
  name: string;
  code: string;
  address: string;
  city: string;
  district: string;
  state: string;
  pincode: string;
  is_active: boolean;
  employee_count: number;
}

const BLANK = {
  name: "",
  code: "",
  address: "",
  city: "",
  district: "",
  state: "Assam",
  pincode: "",
};

export default function ManageCampusesPage() {
  const { can } = useAuth();
  const { push } = useToast();
  const { data, loading, reload } = useApi<Location[]>(
    "/api/locations?include_inactive=true"
  );

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Location | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [busy, setBusy] = useState(false);

  const canCreate = can(P.orgCreate);
  const canEdit = can(P.orgEdit);

  async function save() {
    setBusy(true);
    try {
      if (editing) {
        await api.put(`/api/locations/${editing.id}`, form);
        push("success", "Campus updated");
      } else {
        await api.post("/api/locations", form);
        push("success", "Campus created");
      }
      setOpen(false);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<Location>[] = [
    {
      header: "Campus / Location",
      value: (r) => `${r.name} ${r.code}`,
      cell: (r) => (
        <div className="flex items-center gap-2">
          <MapPin size={17} className="text-[var(--color-green)]" />
          <div>
            <p className="font-semibold">{r.name}</p>
            {r.code && (
              <p className="font-mono text-xs text-[var(--color-ink-faint)]">
                {r.code}
              </p>
            )}
          </div>
        </div>
      ),
    },
    { header: "Address", value: (r) => r.address, cell: (r) => r.address || "—" },
    { header: "District", value: (r) => r.district, cell: (r) => r.district || "—" },
    { header: "State", value: (r) => r.state, cell: (r) => r.state || "—" },
    { header: "PIN", value: (r) => r.pincode, cell: (r) => r.pincode || "—" },
    {
      header: "Employees",
      value: (r) => r.employee_count,
      cell: (r) => r.employee_count,
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
        canEdit ? (
          <button
            onClick={() => {
              setEditing(r);
              setForm({
                name: r.name,
                code: r.code,
                address: r.address,
                city: r.city,
                district: r.district,
                state: r.state,
                pincode: r.pincode,
              });
              setOpen(true);
            }}
            className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
            title="Edit"
          >
            <Pencil size={15} /> <span>Edit</span>
          </button>
        ) : null,
    },
  ];

  return (
    <>
      <div className="mb-2 flex flex-wrap items-start justify-between gap-4">
        <SectionTitle
          title="Campuses & Locations"
          subtitle="Physical locations of the university. A campus is organisational data — it never creates a separate login system."
        />
        {canCreate && (
          <button
            onClick={() => {
              setEditing(null);
              setForm({ ...BLANK });
              setOpen(true);
            }}
            className="btn btn-primary"
          >
            <Plus size={18} /> Add campus
          </button>
        )}
      </div>

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={loading}
        empty="No campuses recorded"
        searchPlaceholder="Search campus, district or PIN"
        pageSize={10}
      />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? `Edit ${editing.name}` : "Add campus"}
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
            <label className="label">Code</label>
            <input
              className="input"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
            />
          </div>
          <div>
            <label className="label">City / Town</label>
            <input
              className="input"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
          </div>
          <div>
            <label className="label">District</label>
            <input
              className="input"
              value={form.district}
              onChange={(e) => setForm({ ...form, district: e.target.value })}
            />
          </div>
          <div>
            <label className="label">State</label>
            <input
              className="input"
              value={form.state}
              onChange={(e) => setForm({ ...form, state: e.target.value })}
            />
          </div>
          <div>
            <label className="label">PIN code</label>
            <input
              className="input"
              value={form.pincode}
              onChange={(e) => setForm({ ...form, pincode: e.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Address</label>
            <textarea
              className="input min-h-20"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
        </div>
        <button
          onClick={save}
          className="btn btn-primary mt-4 w-full"
          disabled={busy || !form.name}
        >
          {busy ? <Spinner /> : editing ? "Save changes" : "Create campus"}
        </button>
      </Modal>
    </>
  );
}
