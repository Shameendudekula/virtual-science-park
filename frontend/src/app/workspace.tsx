import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { getSession, setSession, subscribe, type Session } from "@/lib/session";
import { useCompany, useHealth } from "@/services/queries";
import { Button, Card, ErrorState, LoadingBlock } from "@/components/ui/primitives";

export function useSession(): Session | null {
  return useSyncExternalStore(subscribe, getSession, getSession);
}

/** Public demo sessions can browse everything but not change shared data (enforced by the API). */
export function useReadOnly(): boolean {
  return useSession()?.read_only === true;
}

export const READ_ONLY_HINT = "Read-only demo: sign in with the company's username and password to make changes.";

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
  const [switchApprovedFor, setSwitchApprovedFor] = useState<number | null>(null);
  const matches = session?.company.id === id;
  // A password session (edit access) is never replaced by a read-only demo session without the user's consent.
  const needsConfirm = !matches && session?.read_only === false && !!health.data?.demo_mode && switchApprovedFor !== id;

  useEffect(() => {
    if (matches || needsConfirm || !health.data || !Number.isFinite(id)) return;
    if (health.data.demo_mode) {
      setError(null);
      qc.removeQueries({ queryKey: ["workspace"] });
      demoLogin(id).catch(setError);
    }
  }, [matches, needsConfirm, health.data, id, qc]);

  if (!Number.isFinite(id)) return <Navigate to="/app" replace />;
  if (error) return <div className="p-8"><ErrorState error={error} title="Could not open this workspace" onRetry={() => navigate(0)} /></div>;
  if (health.isError) return <div className="p-8"><ErrorState error={health.error} title="The API is not reachable" onRetry={() => health.refetch()} /></div>;
  if (needsConfirm && session) {
    return (
      <SwitchToDemoPrompt current={session.company.name} targetId={id}
        onStay={() => navigate(`/app/${session.company.id}/focus`)}
        onSignIn={() => navigate(`/login?company=${id}`)}
        onContinue={() => setSwitchApprovedFor(id)} />
    );
  }
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

function SwitchToDemoPrompt({ current, targetId, onStay, onSignIn, onContinue }: {
  current: string; targetId: number; onStay: () => void; onSignIn: () => void; onContinue: () => void;
}) {
  const target = useCompany(targetId).data?.name ?? "this company";
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <Card role="alertdialog" aria-labelledby="switch-title" aria-describedby="switch-desc" className="w-full max-w-lg p-6">
        <h1 id="switch-title" className="text-[17px] font-semibold text-ink">Leave your signed-in workspace?</h1>
        <p id="switch-desc" className="mt-2 text-[13.5px] leading-relaxed text-ink-2">
          You are signed in to <span className="font-medium text-ink">{current}</span> with edit access. Opening {target} as a
          read-only demo will end that session, and you would need to sign in again to make changes.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={onStay} autoFocus>Stay in {current}</Button>
          <Button variant="outline" onClick={onSignIn}>Sign in to {target}</Button>
          <Button variant="ghost" onClick={onContinue}>Open read-only demo</Button>
        </div>
      </Card>
    </div>
  );
}
