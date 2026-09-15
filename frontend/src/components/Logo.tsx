"use client";

export function Logo({
  size = 44,
  light = false,
  showText = true,
}: {
  size?: number;
  light?: boolean;
  showText?: boolean;
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
      {showText && <div className="leading-tight">
        <div
          className="text-[11px] font-medium tracking-wide"
          style={{ color: light ? "rgba(255,255,255,0.75)" : "var(--color-ink-faint)" }}
        >
          Veterinary &amp; Fisheries University
        </div>
      </div>}
    </div>
  );
}
