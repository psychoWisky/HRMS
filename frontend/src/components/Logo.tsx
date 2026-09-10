"use client";

export function Logo({
  size = 44,
  light = false,
}: {
  size?: number;
  light?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <img
        src="/avfu_logo.png"
        alt="AVFU Logo"
        width={size}
        height={size}
        className="object-contain shrink-0"
        style={{ width: size, height: size }}
      />
      <div className="leading-tight">
        <div
          className="text-xl font-bold"
          style={{ color: light ? "#fff" : "var(--color-green-deep)" }}
        >
          AVFU&nbsp;HRMS
        </div>
        <div
          className="text-[11px] font-medium tracking-wide"
          style={{ color: light ? "rgba(255,255,255,0.75)" : "var(--color-ink-faint)" }}
        >
          Veterinary &amp; Fisheries University
        </div>
      </div>
    </div>
  );
}
