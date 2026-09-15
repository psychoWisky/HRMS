"use client";

/**
 * The fixed AVFU University Organogram.
 *
 * This is the statutory top structure of the university (Chancellor → Vice-
 * Chancellor → Registrar / Financial Officer → Deans / Directors / Controller
 * of Examination / Librarian → their sub-roles). It never changes with the
 * editable org-unit tree below it, so it is drawn here as a static diagram
 * matching the client's Organogram_Hierarchy reference.
 */

function Box({
  children,
  bold,
  wide,
}: {
  children: React.ReactNode;
  bold?: boolean;
  wide?: boolean;
}) {
  return (
    <div
      className={`rounded-md border bg-[var(--color-surface)] px-3 py-2 text-center text-[13px] leading-tight ${bold ? "font-bold" : "font-medium"
        } ${wide ? "min-w-[200px]" : "min-w-[150px]"}`}
      style={{ borderColor: "var(--color-line-strong)" }}
    >
      {children}
    </div>
  );
}

function Connector({ h = 18 }: { h?: number }) {
  return (
    <div
      className="mx-auto w-px bg-[var(--color-line-strong)]"
      style={{ height: h }}
    />
  );
}

const DEANS = [
  "Dean, Faculty of Veterinary Science, Khanapara",
  "Associate Dean, Lakhimpur College of Veterinary Science, Joyhing",
  "Dean, Faculty of Fisheries Science, Raha",
  "HoDs",
];

const DIRECTORS: [string, string | null][] = [
  ["Director of Research", "Deputy Director of Research · Chief Scientists (LRS Mandira, GRS Burnihat)"],
  ["Director of Post-Graduate Studies", null],
  ["Director of Extension Education", "Associate Director of Extension Education"],
  ["Director of Student Welfare", "Deputy Director of Student Welfare"],
  ["Director of Physical Plant", "Engineers (Civil, Electrical, Architect)"],
];

export function UniversityOrganogram() {
  return (
    <div className="card overflow-x-auto p-6">
      <div className="mx-auto flex min-w-[720px] flex-col items-center">
        <Box bold wide>
          CHANCELLOR
          <div className="text-[11px] font-normal text-[var(--color-ink-faint)]">
            (Governor of Assam)
          </div>
        </Box>
        <Connector />

        <div className="flex items-center gap-4">
          <Box>Board of Management</Box>
          <div className="flex flex-col items-center">
            <Box bold wide>
              VICE-CHANCELLOR
            </Box>
          </div>
          <Box>Academic Council</Box>
        </div>
        <Connector />

        <div className="flex items-start gap-6">
          <Box>Registrar</Box>
          <Box>Financial Officer</Box>
        </div>
        <Connector h={22} />

        <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
          {/* Deans column */}
          <div className="flex flex-col items-center gap-2">
            <Box bold>Deans</Box>
            {DEANS.map((d) => (
              <Box key={d}>{d}</Box>
            ))}
          </div>

          {/* Directors column */}
          <div className="flex flex-col items-center gap-2 md:col-span-2">
            <Box bold>Directors</Box>
            {DIRECTORS.map(([role, sub]) => (
              <div key={role} className="flex w-full flex-col items-center gap-1">
                <Box wide>{role}</Box>
                {sub && (
                  <>
                    <Connector h={10} />
                    <div
                      className="rounded-md border border-dashed px-3 py-1.5 text-center text-[11px] text-[var(--color-ink-soft)]"
                      style={{ borderColor: "var(--color-line-strong)" }}
                    >
                      {sub}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>

          {/* Standalone offices */}
          <div className="flex flex-col items-center gap-2">
            <Box bold>Other Offices</Box>
            <Box>Controller of Examination</Box>
            <div className="flex w-full flex-col items-center gap-1">
              <Box>Librarian</Box>
              <Connector h={10} />
              <div
                className="rounded-md border border-dashed px-3 py-1.5 text-center text-[11px] text-[var(--color-ink-soft)]"
                style={{ borderColor: "var(--color-line-strong)" }}
              >
                Deputy Librarian
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
