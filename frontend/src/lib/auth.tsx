"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, clearToken, getToken, setToken } from "./api";

export interface CurrentUser {
  id: number;
  email: string;
  role: string;
  role_name: string;
  permissions: string[];
  must_change_password: boolean;
  employee_id: number | null;
  hrms_employee_id: string | null;
  full_name: string;
  designation: string | null;
  org_unit: string | null;
  kyc_status: string | null;
  managed_org_unit_id: number | null;
  managed_org_unit_name: string | null;
}

interface LoginResult {
  access_token: string;
  must_change_password: boolean;
  full_name: string;
  role: string;
}

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => void;
  refresh: () => Promise<void>;
  can: (...permissions: string[]) => boolean;
  canAny: (...permissions: string[]) => boolean;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.get<CurrentUser>("/api/auth/me"));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<LoginResult>("/api/auth/login", {
      email,
      password,
    });
    setToken(res.access_token);
    const me = await api.get<CurrentUser>("/api/auth/me");
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    window.location.href = "/login";
  }, []);

  const can = useCallback(
    (...permissions: string[]) =>
      !!user && permissions.every((p) => user.permissions.includes(p)),
    [user]
  );

  const canAny = useCallback(
    (...permissions: string[]) =>
      !!user && permissions.some((p) => user.permissions.includes(p)),
    [user]
  );

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, refresh, can, canAny }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
