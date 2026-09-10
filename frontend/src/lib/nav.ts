import {
  Building2,
  ClipboardCheck,
  FileBarChart2,
  Inbox,
  KeyRound,
  LayoutDashboard,
  ListTree,
  MapPin,
  Network,
  ScrollText,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  User,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { P } from "./perms";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Shown when the user holds ANY of these permissions. Empty = always. */
  anyOf: string[];
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, anyOf: [] },
      {
        label: "Employee Directory",
        href: "/directory",
        icon: Users,
        anyOf: [P.directoryRead],
      },
      {
        label: "Establishment Hierarchy",
        href: "/organization",
        icon: ListTree,
        anyOf: [P.orgRead],
      },
    ],
  },
  {
    title: "Verification",
    items: [
      {
        label: "New Submissions",
        href: "/manage/submissions",
        icon: Inbox,
        anyOf: [P.submissionReview],
      },
      {
        label: "Employee Documents",
        href: "/manage/kyc",
        icon: ShieldCheck,
        anyOf: [P.kycVerify],
      },
    ],
  },
  {
    title: "Administration",
    items: [
      {
        label: "Employees",
        href: "/manage/employees",
        icon: UsersRound,
        anyOf: [P.employeeRead],
      },
      {
        label: "Organisation Structure",
        href: "/manage/org-units",
        icon: Building2,
        anyOf: [P.structureManage, P.orgEdit, P.orgCreate],
      },
      {
        label: "Campuses",
        href: "/manage/campuses",
        icon: MapPin,
        anyOf: [P.orgCreate, P.orgEdit],
      },
      {
        label: "Designations",
        href: "/manage/designations",
        icon: ScrollText,
        anyOf: [P.designationManage],
      },
      {
        label: "Posts & Vacancies",
        href: "/manage/posts",
        icon: ClipboardCheck,
        anyOf: [P.postManage],
      },
      {
        label: "Reporting Hierarchy",
        href: "/manage/reporting",
        icon: Network,
        anyOf: [P.reportingManage],
      },
      {
        label: "Custom Fields",
        href: "/manage/custom-fields",
        icon: SlidersHorizontal,
        anyOf: [P.customFieldManage],
      },
      {
        label: "Reports",
        href: "/manage/reports",
        icon: FileBarChart2,
        anyOf: [P.reportRead],
      },
    ],
  },
  {
    title: "My Account",
    items: [
      { label: "My Profile", href: "/profile", icon: User, anyOf: [] },
      {
        label: "Change Password",
        href: "/change-password",
        icon: KeyRound,
        anyOf: [P.passwordChangeOwn],
      },
    ],
  },
  {
    title: "System",
    items: [
      {
        label: "Users & Roles",
        href: "/manage/users",
        icon: Users,
        anyOf: [P.userManage],
      },
      {
        label: "Audit Logs",
        href: "/manage/audit",
        icon: ScrollText,
        anyOf: [P.auditRead],
      },
      {
        label: "Settings",
        href: "/manage/settings",
        icon: Settings,
        anyOf: [P.settingsManage],
      },
    ],
  },
];

export function navForPermissions(permissions: string[]): NavGroup[] {
  const has = (codes: string[]) =>
    codes.length === 0 || codes.some((c) => permissions.includes(c));
  return NAV.map((g) => ({ ...g, items: g.items.filter((i) => has(i.anyOf)) }))
    .filter((g) => g.items.length > 0);
}
