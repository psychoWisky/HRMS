"use client";

import { useEffect, useMemo, useState } from "react";
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
 * Cascading College → Establishment | Department → Section/Unit/Cell picker.
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

  const [universityId, setUniversityId] = useState("");
  const [collegeId, setCollegeId] = useState("");
  const [establishmentId, setEstablishmentId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [sectionId, setSectionId] = useState("");

  // Hydrate the cascade from an incoming `value`.
  useEffect(() => {
    if (!value || units.length === 0) {
      setUniversityId("");
      setCollegeId("");
      setEstablishmentId("");
      setDepartmentId("");
      setSectionId("");
      return;
    }
    // Walk up from the selected unit collecting each level.
    let cur: Unit | undefined = byId.get(value);
    let university = "";
    let college = "";
    let establishment = "";
    let department = "";
    let section = "";
    const guard = new Set<number>();
    while (cur && !guard.has(cur.id)) {
      guard.add(cur.id);
      if (cur.kind === "university") university = String(cur.id);
      else if (cur.kind === "college") college = String(cur.id);
      else if (cur.kind === "establishment") establishment = String(cur.id);
      else if (cur.kind === "department") department = String(cur.id);
      else if (cur.kind === "section") section = String(cur.id);
      cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
    }
    setUniversityId(university);
    setCollegeId(college);
    setEstablishmentId(establishment);
    setDepartmentId(department);
    setSectionId(section);
  }, [value, units, byId]);

  const universities = units.filter((u) => u.kind === "university" && u.is_active);
  const colleges = units.filter(
    (u) =>
      u.kind === "college" &&
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
    onChange(deepest ? Number(deepest) : null);
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
          College {required ? "*" : ""}
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
            setDepartmentId(v);
            setSectionId("");
            emit(universityId, collegeId, establishmentId, v, "");
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
