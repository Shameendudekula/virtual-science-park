import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { WorkspaceGate } from "@/app/workspace";
import { AppShell } from "@/components/layout/AppShell";
import { Button, EmptyState, LoadingBlock } from "@/components/ui/primitives";
import { ApiError } from "@/lib/api";
import { useCompanies } from "@/services/queries";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";

const Focus = lazy(() => import("@/pages/Focus"));
const Overview = lazy(() => import("@/pages/Overview"));
const CompanyIntelligence = lazy(() => import("@/pages/CompanyIntelligence"));
const Opportunities = lazy(() => import("@/pages/Opportunities"));
const TechnologyRadar = lazy(() => import("@/pages/TechnologyRadar"));
const Collaboration = lazy(() => import("@/pages/Collaboration"));
const Recommendations = lazy(() => import("@/pages/Recommendations"));
const Compare = lazy(() => import("@/pages/Tools").then((m) => ({ default: m.Compare })));
const Brief = lazy(() => import("@/pages/Tools").then((m) => ({ default: m.Brief })));
const SearchPage = lazy(() => import("@/pages/Tools").then((m) => ({ default: m.SearchPage })));
const DataSources = lazy(() => import("@/pages/Admin").then((m) => ({ default: m.DataSources })));
const Members = lazy(() => import("@/pages/Admin").then((m) => ({ default: m.Members })));
const SettingsPage = lazy(() => import("@/pages/Admin").then((m) => ({ default: m.SettingsPage })));

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
      },
    },
  });
}

function Page({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingBlock rows={4} />}>{children}</Suspense>;
}

function DefaultWorkspace() {
  const { data, isLoading } = useCompanies(true);
  if (isLoading) return <div className="p-8"><LoadingBlock rows={2} /></div>;
  const first = data?.items.find((c) => c.slug === "ocean-harvesting") ?? data?.items[0];
  return first ? <Navigate to={`/app/${first.id}/focus`} replace /> : <div className="p-8"><EmptyState title="No company profiles yet" description="Start the backend so it can seed the demonstration data." /></div>;
}

function NotFound() {
  return <div className="p-10"><EmptyState title="Page not found" description="The page you were looking for does not exist." action={<Link to="/"><Button variant="outline">Back to start</Button></Link>} /></div>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/app" element={<DefaultWorkspace />} />
      <Route path="/app/:companyId" element={<WorkspaceGate><AppShell /></WorkspaceGate>}>
        <Route index element={<Navigate to="focus" replace />} />
        <Route path="focus" element={<Page><Focus /></Page>} />
        <Route path="overview" element={<Page><Overview /></Page>} />
        <Route path="company" element={<Page><CompanyIntelligence /></Page>} />
        <Route path="opportunities" element={<Page><Opportunities /></Page>} />
        <Route path="technologies" element={<Page><TechnologyRadar /></Page>} />
        <Route path="collaboration" element={<Page><Collaboration /></Page>} />
        <Route path="recommendations" element={<Page><Recommendations /></Page>} />
        <Route path="compare" element={<Page><Compare /></Page>} />
        <Route path="brief" element={<Page><Brief /></Page>} />
        <Route path="search" element={<Page><SearchPage /></Page>} />
        <Route path="sources" element={<Page><DataSources /></Page>} />
        <Route path="members" element={<Page><Members /></Page>} />
        <Route path="settings" element={<Page><SettingsPage /></Page>} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

const client = makeQueryClient();

export default function App() {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
