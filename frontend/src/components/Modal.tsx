"use client";

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

export function Modal({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  /** Widen the panel for detail views such as KYC verification. */
  wide?: boolean;
}) {
  // Close on Escape + lock background scroll while open
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          // The backdrop is the scroll container. Clicking it (outside the panel) closes.
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[var(--color-green-deep)]/40 p-4 backdrop-blur-sm sm:items-center sm:p-6"
        >
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.98 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            // Stop clicks inside the panel from bubbling to the backdrop.
            onClick={(e) => e.stopPropagation()}
            className={`relative my-auto flex max-h-[90vh] w-full flex-col bg-[var(--color-surface)] ${
              wide ? "max-w-4xl" : "max-w-lg"
            }`}
            style={{
              border: "1.5px solid var(--color-line)",
              borderRadius: "var(--radius)",
              boxShadow: "var(--shadow-md)",
            }}
          >
            {/* Sticky header */}
            <div
              className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b bg-[var(--color-surface)] px-7 py-5"
              style={{ borderColor: "var(--color-line)", borderRadius: "var(--radius) var(--radius) 0 0" }}
            >
              <div className="flex items-center gap-3">
                <span className="accent-bar" />
                <h2 className="text-2xl font-bold text-[var(--color-ink)]">{title}</h2>
              </div>
              <button
                onClick={onClose}
                aria-label="Close"
                className="p-1.5 text-[var(--color-ink-faint)] transition-colors hover:bg-[var(--color-surface-2)] hover:text-[var(--color-ink)]"
                style={{ borderRadius: "var(--radius-sm)" }}
              >
                <X size={22} />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="overflow-y-auto px-7 py-6">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
