"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useApi } from "@/lib/useApi";
import { orgUnitLabel } from "@/lib/format";

interface Unit {
  id: number;
  kind: string;
  sub_kind: string;
  parent_id: number | null;
  name: string;
  path: string;
  is_active: boolean;
}

/**
 * Cascading University → College → Establishment | Department → Section/Unit/Cell picker.
 *
 * Emits the id of the deepest unit the user selected (any level) via
 * `onChange`. When `value` is set, the cascade auto-populates from the
 * unit's ancestor chain.
 */
export function OrgUnitPicker({
  value,
  onChange,
  required,
  disabled,
}: {
  value: number | null;
  onChange: (id: number | null) => void;
  required?: boolean;
  disabled?: boolean;
}) {
  const { data } = useApi<Unit[]>("/api/org-units?limit=1000");
  const units = useMemo(() => data ?? [], [data]);
  const byId = useMemo(
    () => new Map(units.map((u) => [u.id, u])),
    [units]
  );
  // Some databases still store the University itself as a top-level
  // "college" with the real colleges beneath it (the state before the
  // "make AVFU the University" repair on Manage → Org units). Treat such a
  // row as the University so it never shows up in, or overwrites, the
  // College / University field.
  const levelOf = useMemo(() => {
    const parentsOfColleges = new Set(
      units.filter((u) => u.kind === "college" && u.parent_id).map((u) => u.parent_id)
    );
    return (u: Unit) =>
      u.kind === "college" && !u.parent_id && parentsOfColleges.has(u.id)
        ? "university"
        : u.kind;
  }, [units]);

  const [universityId, setUniversityId] = useState("");
  const [collegeId, setCollegeId] = useState("");
  const [establishmentId, setEstablishmentId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [sectionId, setSectionId] = useState("");
  // The id this picker last sent up. When the parent echoes it back as
  // `value` we keep the user's own selections instead of re-deriving them.
  const lastEmitted = useRef<number | null | undefined>(undefined);

  // Hydrate the cascade from an incoming `value`.
  useEffect(() => {
    if (units.length === 0) return;
    if (lastEmitted.current !== undefined && value === lastEmitted.current) return;
    lastEmitted.current = undefined;
    if (!value) {
      setUniversityId("");
      setCollegeId("");
      setEstablishmentId("");
      setDepartmentId("");
      setSectionId("");
      return;
    }
    // Walk up from the selected unit, keeping the NEAREST unit of each level.
    const found: Record<string, string> = {};
    let cur: Unit | undefined = byId.get(value);
    const guard = new Set<number>();
    while (cur && !guard.has(cur.id)) {
      guard.add(cur.id);
      const level = levelOf(cur);
      if (!found[level]) found[level] = String(cur.id);
      cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
    }
    setUniversityId(found.university ?? "");
    setCollegeId(found.college ?? "");
    setEstablishmentId(found.establishment ?? "");
    setDepartmentId(found.department ?? "");
    setSectionId(found.section ?? "");
  }, [value, units, byId, levelOf]);

  const universities = units.filter((u) => levelOf(u) === "university" && u.is_active);
  const colleges = units.filter(
    (u) =>
      levelOf(u) === "college" &&
      u.is_active &&
      (!universityId || String(u.parent_id) === universityId)
  );
  // An establishment can sit under the chosen College, or — if no College is
  // chosen (or the establishment isn't in any) — directly under the
  // University, matching the backend's "central office" attachment.
  const establishments = units.filter(
    (u) =>
      u.kind === "establishment" &&
      u.is_active &&
      ((collegeId && String(u.parent_id) === collegeId) ||
        (!collegeId && universityId && String(u.parent_id) === universityId) ||
        (!collegeId && !universityId))
  );
  const departments = units.filter(
    (u) =>
      u.kind === "department" &&
      u.is_active &&
      ((collegeId && String(u.parent_id) === collegeId) ||
        (establishmentId && String(u.parent_id) === establishmentId) ||
        (!collegeId && universityId && String(u.parent_id) === universityId) ||
        (!collegeId && !universityId))
  );
  const parentForSections = departmentId || establishmentId;
  const sections = units.filter(
    (u) =>
      u.kind === "section" &&
      u.is_active &&
      parentForSections &&
      String(u.parent_id) === parentForSections
  );

  function emit(
    university: string,
    college: string,
    establishment: string,
    department: string,
    section: string
  ) {
    const deepest =
      section || department || establishment || college || university || "";
    const id = deepest ? Number(deepest) : null;
    lastEmitted.current = id;
    onChange(id);
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <label className="label">University</label>
        <select
          className="input"
          value={universityId}
          disabled={disabled}
          onChange={(e) => {
            const v = e.target.value;
            setUniversityId(v);
            setCollegeId("");
            setEstablishmentId("");
            setDepartmentId("");
            setSectionId("");
            emit(v, "", "", "", "");
          }}
        >
          <option value="">— (any)</option>
          {universities.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label">
          College / University {required ? "*" : ""}
        </label>
        <select
          className="input"
          value={collegeId}
          disabled={disabled}
          onChange={(e) => {
            const v = e.target.value;
            setCollegeId(v);
            setEstablishmentId("");
            setDepartmentId("");
            setSectionId("");
            emit(universityId, v, "", "", "");
          }}
        >
          <option value="">
            {universityId ? "— (central office, no college)" : "Select…"}
          </option>
          {colleges.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label">Establishment</label>
        <select
          className="input"
          value={establishmentId}
          disabled={disabled}
          onChange={(e) => {
            const v = e.target.value;
            setEstablishmentId(v);
            setDepartmentId("");
            setSectionId("");
            emit(universityId, collegeId, v, "", "");
          }}
        >
          <option value="">
            {collegeId ? "— (whole college)" : "— (whole university)"}
          </option>
          {establishments.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label">Department</label>
        <select
          className="input"
          value={departmentId}
          disabled={disabled}
          onChange={(e) => {
            const v = e.target.value;
            // Departments usually sit directly under a College — only keep
            // the Establishment when this department really belongs to it,
            // so the form never shows a placement that won't be saved.
            const dept = v ? byId.get(Number(v)) : undefined;
            const est =
              dept && String(dept.parent_id) === establishmentId ? establishmentId : v ? "" : establishmentId;
            setEstablishmentId(est);
            setDepartmentId(v);
            setSectionId("");
            emit(universityId, collegeId, est, v, "");
          }}
        >
          <option value="">— (none)</option>
          {departments.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="label">Section / Unit / Cell</label>
        <select
          className="input"
          value={sectionId}
          disabled={disabled || !parentForSections}
          onChange={(e) => {
            const v = e.target.value;
            setSectionId(v);
            emit(universityId, collegeId, establishmentId, departmentId, v);
          }}
        >
          <option value="">— (office level)</option>
          {sections.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name} ({orgUnitLabel("section", u.sub_kind)})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
