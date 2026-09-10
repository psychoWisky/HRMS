"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useToast } from "@/components/Toast";
import { fmtDateTime } from "@/lib/format";
import {
  Empty,
  MotionCard,
  SectionTitle,
  Skeleton,
  Spinner,
} from "@/components/ui";

interface Setting {
  id: number;
  key: string;
  value: string;
  description: string;
  updated_at: string;
}

export default function SettingsPage() {
  const { data, loading, reload } = useApi<Setting[]>("/api/admin/settings");
  const { push } = useToast();
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    setValues(Object.fromEntries(data.map((s) => [s.key, s.value])));
  }, [data]);

  async function save(key: string) {
    setSaving(key);
    try {
      await api.put(`/api/admin/settings/${key}`, { value: values[key] ?? "" });
      push("success", `${key} updated`);
      reload();
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(null);
    }
  }

  if (loading) return <Skeleton className="h-72" />;

  return (
    <>
      <SectionTitle
        title="System Configuration"
        subtitle="Values used across the HRMS. Changes are recorded in the audit log."
      />

      {(data ?? []).length === 0 ? (
        <Empty message="No settings recorded" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {(data ?? []).map((s) => (
            <MotionCard key={s.key}>
              <p className="font-mono text-sm font-semibold text-[var(--color-green)]">
                {s.key}
              </p>
              <p className="mb-3 text-sm text-[var(--color-ink-soft)]">
                {s.description}
              </p>
              <div className="flex gap-2">
                <input
                  className="input"
                  value={values[s.key] ?? ""}
                  onChange={(e) =>
                    setValues((v) => ({ ...v, [s.key]: e.target.value }))
                  }
                />
                <button
                  onClick={() => save(s.key)}
                  className="btn btn-primary px-4"
                  disabled={saving === s.key}
                >
                  {saving === s.key ? <Spinner size={18} /> : <Save size={18} />}
                </button>
              </div>
              <p className="mt-2 text-xs text-[var(--color-ink-faint)]">
                Last updated {fmtDateTime(s.updated_at)}
              </p>
            </MotionCard>
          ))}
        </div>
      )}
    </>
  );
}
