"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  Info,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import { Logo } from "@/components/Logo";
import { Spinner } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

type Mode = "login" | "forgot" | "reset";

export default function LoginPage() {
  const { login } = useAuth();
  const { push } = useToast();
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("login");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [notice, setNotice] = useState("");

  async function submitLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const me = await login(email.trim(), password);
      push("success", `Welcome, ${me.full_name.split(" ").slice(-1)[0]}`);
      router.replace(me.must_change_password ? "/change-password" : "/dashboard");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Sign in failed");
      setBusy(false);
    }
  }

  async function submitForgot(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api.post<{ message: string; reset_token?: string }>(
        "/api/auth/forgot-password",
        { email: email.trim() }
      );
      setNotice(res.message);
      if (res.reset_token) {
        setToken(res.reset_token);
        setMode("reset");
        push("info", "Reset token issued — set a new password below");
      } else {
        push("info", "Request submitted");
      }
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitReset(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/api/auth/reset-password", {
        token: token.trim(),
        new_password: newPassword,
      });
      push("success", "Password reset. Please sign in.");
      setMode("login");
      setPassword("");
      setNewPassword("");
    } catch (err) {
      push("error", err instanceof ApiError ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-stretch">
      {/* Brand panel */}
      <div
        className="relative hidden w-[44%] flex-col justify-between p-12 text-white lg:flex"
        style={{ background: "var(--color-green)" }}
      >
        <Logo light size={52} />
        <div className="relative">
          <h2 className="text-4xl font-bold leading-tight">
            Human Resource
            <br />
            Management System
          </h2>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-white/85">
            One centralised system for every campus, office, faculty,
            directorate and research station of Assam Veterinary and Fishery
            University.
          </p>
          <ul className="mt-6 space-y-2 text-white/90">
            {[
              "University-wide employee directory",
              "Organisational and reporting hierarchy",
              "Sanctioned posts and vacancies",
              "New-employee document verification",
            ].map((t) => (
              <li key={t} className="flex items-center gap-2">
                <CheckCircle2 size={18} /> {t}
              </li>
            ))}
          </ul>
        </div>
        <div className="relative flex items-center gap-2 text-sm text-white/75">
          <ShieldCheck size={18} /> Secure government-grade access
        </div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-1 items-center justify-center bg-[var(--color-bg)] p-5">
        <div
          className="w-full max-w-md rounded-3xl bg-[var(--color-surface)] p-8 sm:p-10 [&_.btn]:rounded-xl [&_.input]:rounded-xl"
          style={{
            border: "1.5px solid var(--color-line)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          <div className="mb-6 lg:hidden">
            <Logo size={46} />
          </div>

          <AnimatePresence mode="wait">
            {mode === "login" && (
              <motion.form
                key="login"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                onSubmit={submitLogin}
                className="space-y-4"
              >
                <h1 className="text-2xl font-bold">Sign in to AVFU HRMS</h1>
                <p className="-mt-2 text-sm text-[var(--color-ink-faint)]">
                  Use the email and password issued by the HRMS administrator.
                </p>
                <div>
                  <label className="label">Email address</label>
                  <input
                    className="input"
                    type="email"
                    autoComplete="username"
                    placeholder="you@avfu.ac.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="label">Password</label>
                  <div className="relative">
                    <input
                      className="input pr-12"
                      type={show ? "text" : "password"}
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShow((s) => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-ink-faint)] hover:text-[var(--color-green)]"
                      tabIndex={-1}
                      aria-label={show ? "Hide password" : "Show password"}
                    >
                      {show ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  className="btn btn-primary w-full"
                  disabled={busy}
                >
                  {busy ? (
                    <Spinner />
                  ) : (
                    <>
                      Sign in <ArrowRight size={18} />
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("forgot");
                    setNotice("");
                  }}
                  className="w-full text-center text-sm font-semibold text-[var(--color-green)] hover:underline"
                >
                  Forgot your password?
                </button>
                <div
                  className="mt-2 flex gap-2 rounded-xl p-3 text-xs leading-relaxed text-[var(--color-ink-soft)]"
                  style={{ background: "var(--color-surface-2)" }}
                >
                  <Info size={16} className="mt-0.5 shrink-0" />
                  <span>
                    Sign-in is for Administrator, HR and Department Head
                    accounts only. Accounts are created by the HRMS
                    administrator.
                  </span>
                </div>
              </motion.form>
            )}

            {mode === "forgot" && (
              <motion.form
                key="forgot"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
                onSubmit={submitForgot}
                className="space-y-4"
              >
                <h1 className="text-2xl font-bold">Reset your password</h1>
                <p className="-mt-2 text-sm text-[var(--color-ink-faint)]">
                  Enter your registered AVFU email address.
                </p>
                <div>
                  <label className="label">Email address</label>
                  <input
                    className="input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@avfu.ac.in"
                    required
                  />
                </div>
                {notice && (
                  <p className="rounded-xl bg-[var(--color-surface-2)] p-3 text-sm text-[var(--color-ink-soft)]">
                    {notice}
                  </p>
                )}
                <button
                  type="submit"
                  className="btn btn-primary w-full"
                  disabled={busy}
                >
                  {busy ? <Spinner /> : "Request reset"}
                </button>
                <button
                  type="button"
                  onClick={() => setMode("reset")}
                  className="w-full text-center text-sm font-semibold text-[var(--color-green)] hover:underline"
                >
                  I already have a reset token
                </button>
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className="w-full text-center text-sm text-[var(--color-ink-faint)] hover:underline"
                >
                  Back to sign in
                </button>
              </motion.form>
            )}

            {mode === "reset" && (
              <motion.form
                key="reset"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
                onSubmit={submitReset}
                className="space-y-4"
              >
                <h1 className="text-2xl font-bold">Set a new password</h1>
                <div>
                  <label className="label">Reset token</label>
                  <input
                    className="input font-mono text-sm"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Paste the token you were given"
                    required
                  />
                </div>
                <div>
                  <label className="label">New password</label>
                  <input
                    className="input"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 8 characters, with a letter and a digit"
                    required
                    minLength={8}
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary w-full"
                  disabled={busy}
                >
                  {busy ? <Spinner /> : "Reset password"}
                </button>
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className="w-full text-center text-sm text-[var(--color-ink-faint)] hover:underline"
                >
                  Back to sign in
                </button>
              </motion.form>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
