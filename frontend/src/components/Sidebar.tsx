"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { navForPermissions } from "@/lib/nav";
import { Logo } from "./Logo";

export function Sidebar({
  permissions,
  role,
  onNavigate,
}: {
  permissions: string[];
  role?: string;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const groups = navForPermissions(permissions, role);

  return (
    <aside className="sticky top-0 flex h-screen max-h-screen w-[290px] shrink-0 flex-col border-r border-[var(--color-line)] bg-[var(--color-surface)]">
      <div className="border-b border-[var(--color-line)] px-6 py-6">
        <div className="flex flex-col items-center text-center">
          <Logo size={84} showText={false} />
          <p className="mt-3 max-w-[220px] text-sm font-bold leading-snug text-[var(--color-green-deep)]">
            AVFU Human Resource Management System
          </p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group.title} className="mb-5">
            <p className="px-3 pb-2 text-[11px] font-bold uppercase tracking-wider text-[var(--color-ink-faint)]">
              {group.title}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active =
                  pathname === item.href || pathname.startsWith(item.href + "/");
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      className="group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors"
                      style={{
                        color: active ? "#fff" : "var(--color-ink-soft)",
                      }}
                    >
                      {active && (
                        <motion.span
                          layoutId="nav-active"
                          className="absolute inset-0 rounded-xl"
                          style={{
                            background:
                              "linear-gradient(180deg, var(--color-green-soft), var(--color-green))",
                            boxShadow: "0 8px 18px -10px rgba(94,20,31,0.6)",
                          }}
                          transition={{ type: "spring", stiffness: 380, damping: 34 }}
                        />
                      )}
                      <Icon
                        size={20}
                        className="relative shrink-0 transition-colors"
                        style={{
                          color: active ? "#fff" : "var(--color-green-soft)",
                        }}
                      />
                      <span className="relative">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
