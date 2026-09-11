"use client";

import { useState } from "react";
import { Copy, KeyRound, Power, ShieldCheck } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/perms";
import { useToast } from "@/components/Toast";
import { Modal } from "@/components/Modal";
import { Column, DataTable } from "@/components/DataTable";
import { OrgUnitSelect } from "@/components/OrgUnitSelect";
import { fmtDateTime, titleize } from "@/lib/format";
import { SectionTitle, Spinner, StatusBadge } from "@/components/ui";

interface UserRow {
  id: number;
  email: string;
  role_code: string;
  role_name: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  employee_id: number | null;
  employee_name: string | null;
  hrms_employee_id: string | null;
  managed_org_unit_id: number | null;
  managed_org_unit_name: string | null;
}

interface RoleRow {
  id: number;
  code: string;
  name: string;
  description: string;
  is_system: boolean;
  is_active: boolean;
  permissions: string[];
  user_count: number;
}

interface PermissionRow {
  id: number;
  code: string;
  group: string;
  description: string;
}

interface Credential {
  login_email: string;
  temporary_password: string;
  note: string;
}

export default function ManageUsersPage() {
  const { can, user: me } = useAuth();
  const { push } = useToast();
  const [tab, setTab] = useState<"users" | "roles">("users");

  const { data: users, loading, reload } = useApi<UserRow[]>("/api/admin/users");
  const { data: roles, reload: reloadRoles } = useApi<RoleRow[]>("/api/admin/roles");
  const { data: permissions } = useApi<PermissionRow[]>(
    can(P.roleManage) ? "/api/admin/permissions" : null
  );

  const [credential, setCredential] = useState<Credential | null>(null);
  const [editingRole, setEditingRole] = useState<RoleRow | null>(null);
  const [rolePerms, setRolePerms] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const canManageRoles = can(P.roleManage);

  async function resetPassword(row: UserRow) {
    try {
      const cred = await api.post<Credential>(
        `/api/admin/users/${row.id}/reset-password`
      );
      setCredential(cred);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Reset failed");
    }
  }

  async function toggleActive(row: UserRow) {
    try {
      await api.put(`/api/admin/users/${row.id}/activation`, {
        is_active: !row.is_active,
      });
      push("success", `${row.email} ${row.is_active ? "deactivated" : "activated"}`);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  async function changeRole(row: UserRow, code: string) {
    try {
      await api.put(`/api/admin/users/${row.id}/role`, { role_code: code });
      push("success", "Role updated");
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  async function changeScope(row: UserRow, managedUnitId: string) {
    try {
      await api.put(`/api/admin/users/${row.id}/scope`, {
        managed_org_unit_id: managedUnitId ? Number(managedUnitId) : null,
      });
      push("success", "Managed department updated");
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Action failed");
    }
  }

  async function saveRolePermissions() {
    if (!editingRole) return;
    setBusy(true);
    try {
      await api.put(`/api/admin/roles/${editingRole.id}`, {
        permissions: rolePerms,
      });
      push("success", `Permissions updated for ${editingRole.name}`);
      setEditingRole(null);
      reloadRoles();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const userColumns: Column<UserRow>[] = [
    {
      header: "Account",
      value: (r) => `${r.employee_name ?? ""} ${r.email}`,
      cell: (r) => (
        <div>
          <p className="font-semibold">{r.employee_name ?? "—"}</p>
          <p className="text-xs text-[var(--color-ink-faint)]">{r.email}</p>
        </div>
      ),
    },
    {
      header: "HRMS ID",
      value: (r) => r.hrms_employee_id ?? "",
      cell: (r) => (
        <span className="font-mono text-xs">{r.hrms_employee_id ?? "—"}</span>
      ),
    },
    {
      header: "Role",
      value: (r) => r.role_name,
      cell: (r) => (
        <select
          className="input px-2 py-1.5 text-sm"
          value={r.role_code}
          disabled={r.id === me?.id}
          onChange={(e) => changeRole(r, e.target.value)}
        >
          {(roles ?? []).map((role) => (
            <option key={role.code} value={role.code}>
              {role.name}
            </option>
          ))}
        </select>
      ),
    },
    {
      header: "Managed department",
      value: (r) => r.managed_org_unit_name ?? "",
      cell: (r) =>
        r.role_code === "department_head" ? (
          <OrgUnitSelect
            className="min-w-[220px] text-sm"
            value={r.managed_org_unit_id ?? null}
            onChange={(id) => changeScope(r, id ? String(id) : "")}
            placeholder="Not assigned"
          />
        ) : (
          <span className="text-[var(--color-ink-faint)]">
            {r.role_code === "admin" || r.role_code === "hr_admin"
              ? "University-wide"
              : "—"}
          </span>
        ),
    },
    {
      header: "Last sign-in",
      value: (r) => r.last_login_at ?? "",
      cell: (r) => (
        <span className="text-sm">{fmtDateTime(r.last_login_at)}</span>
      ),
    },
    {
      header: "Status",
      value: (r) => (r.is_active ? "Active" : "Inactive"),
      cell: (r) => (
        <div className="space-y-1">
          <StatusBadge
            status={r.is_active ? "active" : "cancelled"}
            label={r.is_active ? "Active" : "Inactive"}
          />
          {r.must_change_password && (
            <p className="text-xs text-[var(--color-warn)]">
              Must change password
            </p>
          )}
        </div>
      ),
    },
    {
      header: "Actions",
      cell: (r) => (
        <div className="flex gap-1.5">
          <button
            onClick={() => resetPassword(r)}
            className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-green)] hover:bg-[var(--color-green-tint)]"
            title="Reset password"
          >
            <KeyRound size={16} />
          </button>
          <button
            onClick={() => toggleActive(r)}
            className="rounded-lg border border-[var(--color-line)] p-1.5 text-[var(--color-danger)] hover:bg-[#fbf0f0]"
            title={r.is_active ? "Deactivate" : "Activate"}
            disabled={r.id === me?.id}
          >
            <Power size={16} />
          </button>
        </div>
      ),
    },
  ];

  const groups = Array.from(new Set((permissions ?? []).map((p) => p.group)));

  return (
    <>
      <SectionTitle
        title="Users & Roles"
        subtitle="Manage login accounts and configure what each role is allowed to do. Every permission here is enforced on the API."
      />

      <div className="mb-5 flex gap-2">
        {(["users", "roles"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="rounded-full border px-4 py-2 text-sm font-semibold transition-colors"
            style={{
              borderColor: tab === t ? "var(--color-green)" : "var(--color-line)",
              background: tab === t ? "var(--color-green)" : "transparent",
              color: tab === t ? "#fff" : "var(--color-ink-soft)",
            }}
          >
            {titleize(t)}
          </button>
        ))}
      </div>

      {tab === "users" ? (
        <DataTable
          columns={userColumns}
          rows={users ?? []}
          loading={loading}
          empty="No user accounts found"
          searchPlaceholder="Search name, login email, HRMS ID or role"
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(roles ?? []).map((role) => (
            <div key={role.id} className="card p-5">
              <div className="mb-2 flex items-center gap-2">
                <ShieldCheck size={20} className="text-[var(--color-green)]" />
                <h3 className="text-lg font-bold">{role.name}</h3>
                {role.is_system && (
                  <span className="rounded-md border border-[var(--color-line)] px-1.5 py-0.5 text-[11px] font-semibold uppercase text-[var(--color-ink-faint)]">
                    System
                  </span>
                )}
              </div>
              <p className="text-sm text-[var(--color-ink-soft)]">
                {role.description}
              </p>
              <p className="mt-3 text-sm text-[var(--color-ink-faint)]">
                {role.permissions.length} permission
                {role.permissions.length === 1 ? "" : "s"} · {role.user_count} user
                {role.user_count === 1 ? "" : "s"}
              </p>
              {canManageRoles && (
                <button
                  onClick={() => {
                    setEditingRole(role);
                    setRolePerms([...role.permissions]);
                  }}
                  className="btn btn-ghost mt-4 w-full"
                >
                  Configure permissions
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Role permission editor */}
      <Modal
        open={!!editingRole}
        onClose={() => setEditingRole(null)}
        title={editingRole ? `Permissions — ${editingRole.name}` : ""}
        wide
      >
        {editingRole && (
          <div className="space-y-5">
            {groups.map((group) => (
              <div key={group}>
                <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-[var(--color-ink-faint)]">
                  {group}
                </h4>
                <div className="grid gap-2 sm:grid-cols-2">
                  {(permissions ?? [])
                    .filter((p) => p.group === group)
                    .map((p) => (
                      <label
                        key={p.code}
                        className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-[var(--color-line)] p-3 hover:bg-[var(--color-surface-2)]"
                      >
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={rolePerms.includes(p.code)}
                          onChange={(e) =>
                            setRolePerms((prev) =>
                              e.target.checked
                                ? [...prev, p.code]
                                : prev.filter((c) => c !== p.code)
                            )
                          }
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-semibold">
                            {p.description}
                          </span>
                          <span className="block font-mono text-xs text-[var(--color-ink-faint)]">
                            {p.code}
                          </span>
                        </span>
                      </label>
                    ))}
                </div>
              </div>
            ))}
            <button
              onClick={saveRolePermissions}
              className="btn btn-primary w-full"
              disabled={busy}
            >
              {busy ? <Spinner /> : "Save permissions"}
            </button>
          </div>
        )}
      </Modal>

      {/* Reset credential */}
      <Modal
        open={!!credential}
        onClose={() => setCredential(null)}
        title="Temporary password issued"
      >
        {credential && (
          <div className="space-y-4">
            <div className="rounded-xl border-2 border-[var(--color-green)] bg-[var(--color-green-tint)] p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                Login email
              </p>
              <p className="font-mono">{credential.login_email}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-ink-faint)]">
                Temporary password
              </p>
              <div className="flex items-center gap-2">
                <p className="font-mono text-lg font-bold">
                  {credential.temporary_password}
                </p>
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(credential.temporary_password);
                    push("success", "Copied");
                  }}
                  className="rounded-lg border border-[var(--color-line)] bg-white p-1.5"
                  title="Copy"
                >
                  <Copy size={15} />
                </button>
              </div>
            </div>
            <p className="text-sm text-[var(--color-ink-soft)]">{credential.note}</p>
            <button
              onClick={() => setCredential(null)}
              className="btn btn-primary w-full"
            >
              Done
            </button>
          </div>
        )}
      </Modal>
    </>
  );
}
