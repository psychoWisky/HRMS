"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, LogOut, ChevronDown } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Avatar } from "./ui";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  if (!user) return null;

  return (
    <header
      className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b px-5 py-3.5"
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-line)",
        boxShadow: "0 1px 3px rgba(15,20,17,0.05)",
      }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onMenu}
          className="rounded-xl p-2 text-[var(--color-green)] hover:bg-[var(--color-surface-2)] lg:hidden"
        >
          <Menu size={24} />
        </button>
        <div>
          <p className="text-sm text-[var(--color-ink-faint)]">{greeting()},</p>
          <p className="text-lg font-semibold leading-tight text-[var(--color-green-deep)]">
            {user.full_name}
          </p>
        </div>
      </div>

      <div className="relative">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2.5 rounded-full border border-[var(--color-line)] bg-white py-1.5 pl-1.5 pr-3 transition-colors hover:border-[var(--color-green-soft)]"
        >
          <Avatar name={user.full_name} size={36} />
          <div className="hidden text-left sm:block">
            <p className="text-sm font-semibold leading-tight text-[var(--color-ink)]">
              {user.hrms_employee_id ?? "—"}
            </p>
            <p className="text-xs text-[var(--color-ink-faint)]">
              {user.role_name}
            </p>
          </div>
          <ChevronDown size={16} className="text-[var(--color-ink-faint)]" />
        </button>

        <AnimatePresence>
          {open && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.97 }}
                transition={{ duration: 0.18 }}
                className="card absolute right-0 z-20 mt-2 w-56 overflow-hidden p-2"
              >
                <div className="px-3 py-2">
                  <p className="font-semibold text-[var(--color-ink)]">
                    {user.full_name}
                  </p>
                  <p className="text-xs text-[var(--color-ink-faint)]">{user.email}</p>
                </div>
                <div className="my-1 h-px bg-[var(--color-line)]" />
                <button
                  onClick={logout}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-[15px] font-medium text-[var(--color-danger)] transition-colors hover:bg-[#fbe9e9]"
                >
                  <LogOut size={18} /> Sign out
                </button>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
}
