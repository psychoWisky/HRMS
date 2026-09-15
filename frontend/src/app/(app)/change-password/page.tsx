"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, ShieldAlert } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import { MotionCard, SectionTitle, Spinner } from "@/components/ui";
import { PasswordInput } from "@/components/PasswordInput";

export default function ChangePasswordPage() {
  const { user, refresh } = useAuth();
  const { push } = useToast();
  const router = useRouter();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const forced = user?.must_change_password ?? false;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== confirm) {
      push("error", "The two new passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.post("/api/auth/change-password", {
        current_password: current,
        new_password: next,
      });
      push("success", "Password changed");
      await refresh();
      router.replace("/dashboard");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Change failed");
      setBusy(false);
    }
  }

  return (
    <>
      <SectionTitle
        title="Change Password"
        subtitle="Choose a password only you know. It is stored as a one-way hash — nobody, including the administrator, can read it."
      />

      {forced && (
        <div
          className="card mb-5 flex gap-3 border-l-4 p-4"
          style={{ borderLeftColor: "var(--color-warn)" }}
        >
          <ShieldAlert
            size={20}
            className="mt-0.5 shrink-0"
            style={{ color: "var(--color-warn)" }}
          />
          <div>
            <p className="font-semibold">You must change your password to continue</p>
            <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
              You are signed in with an initial or temporary password issued by
              the HRMS administrator.
            </p>
          </div>
        </div>
      )}

      <MotionCard className="max-w-lg">
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Current password</label>
            <PasswordInput
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label">New password</label>
            <PasswordInput
              autoComplete="new-password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              minLength={8}
              placeholder="At least 8 characters, with a letter and a digit"
            />
          </div>
          <div>
            <label className="label">Confirm new password</label>
            <PasswordInput
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <button type="submit" className="btn btn-primary w-full" disabled={busy}>
            {busy ? (
              <Spinner />
            ) : (
              <>
                <KeyRound size={18} /> Change password
              </>
            )}
          </button>
        </form>
      </MotionCard>
    </>
  );
}
