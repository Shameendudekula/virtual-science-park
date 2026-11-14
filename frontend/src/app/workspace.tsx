import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { getSession, setSession, subscribe, type Session } from "@/lib/session";
import { useHealth } from "@/services/queries";
import { ErrorState, LoadingBlock } from "@/components/ui/primitives";

export function useSession(): Session | null {
  return useSyncExternalStore(subscribe, getSession, getSession);
}

interface WorkspaceCtx { companyId: number; companyName: string; signOut: () => void }
const Ctx = createContext<WorkspaceCtx | null>(null);

export function useWorkspace(): WorkspaceCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useWorkspace must be used inside a company workspace");
  return v;
}

export async function demoLogin(companyId: number): Promise<Session> {
  const s = await post<Session>("/api/auth/demo-login", { company_id: companyId });
  setSession(s);
  return s;
}

/** Ensures the visitor holds a session for the company in the URL (one login per company workspace). */
export function WorkspaceGate({ children }: { children: ReactNode }) {
  const { companyId } = useParams();
  const id = Number(companyId);
  const session = useSession();
  const health = useHealth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const matches = session?.company.id === id;

  useEffect(() => {
    if (matches || !health.data || !Number.isFinite(id)) return;
    if (health.data.demo_mode) {
      setError(null);
      qc.removeQueries({ queryKey: ["workspace"] });
      demoLogin(id).catch(setError);
    }
  }, [matches, health.data, id, qc]);

  if (!Number.isFinite(id)) return <Navigate to="/app" replace />;
  if (error) return <div className="p-8"><ErrorState error={error} title="Could not open this workspace" onRetry={() => navigate(0)} /></div>;
  if (health.isError) return <div className="p-8"><ErrorState error={health.error} title="The API is not reachable" onRetry={() => health.refetch()} /></div>;
  if (!matches) {
    if (health.data && !health.data.demo_mode) return <Navigate to={`/login?company=${id}`} replace />;
    return <div className="p-8"><LoadingBlock rows={3} label="Opening workspace" /></div>;
  }
  const value: WorkspaceCtx = {
    companyId: id,
    companyName: session!.company.name,
    signOut: () => {
      setSession(null);
      qc.clear();
      navigate("/");
    },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
