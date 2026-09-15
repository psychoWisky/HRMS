"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { Spinner } from "@/components/ui";

const PUBLIC_PATHS = new Set<string>();
const DEPARTMENT_HEAD_BLOCKED_PATHS = [
  "/manage/org-units",
  "/manage/campuses",
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isPublicPath = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      if (!isPublicPath) router.replace("/login");
      return;
    }
    // Initial/temporary credentials must be replaced before anything else.
    if (user.must_change_password && pathname !== "/change-password") {
      router.replace("/change-password");
      return;
    }
    if (
      user.role === "department_head" &&
      DEPARTMENT_HEAD_BLOCKED_PATHS.some(
        (path) => pathname === path || pathname.startsWith(`${path}/`)
      )
    ) {
      router.replace("/dashboard");
    }
  }, [user, loading, router, pathname, isPublicPath]);

  if (loading || (!user && !isPublicPath)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--color-green)]">
        <Spinner size={32} />
      </div>
    );
  }

  if (!user) return null;

  const departmentHeadBlocked =
    user.role === "department_head" &&
    DEPARTMENT_HEAD_BLOCKED_PATHS.some(
      (path) => pathname === path || pathname.startsWith(`${path}/`)
    );
  if (departmentHeadBlocked) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--color-green)]">
        <Spinner size={32} />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:block">
        <Sidebar permissions={user.permissions} role={user.role} />
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="fixed inset-0 z-40 bg-black/30 lg:hidden"
            />
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: "spring", stiffness: 380, damping: 38 }}
              className="fixed inset-y-0 left-0 z-50 lg:hidden"
            >
              <Sidebar
                permissions={user.permissions}
                role={user.role}
                onNavigate={() => setMobileOpen(false)}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenu={() => setMobileOpen(true)} />
        <main className="flex-1 px-5 py-7 sm:px-8">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
