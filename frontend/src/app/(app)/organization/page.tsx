"use client";

import { UniversityOrganogram } from "@/components/UniversityOrganogram";
import { SectionTitle } from "@/components/ui";

export default function OrganizationPage() {
  return (
    <>
      <SectionTitle
        title="AVFU Organisation Hierarchy"
        subtitle="The statutory university organogram."
      />

      <UniversityOrganogram />
    </>
  );
}
