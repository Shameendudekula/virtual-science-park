import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { demoLogin } from "@/app/workspace";
import { Logo } from "@/components/layout/AppShell";
import { Button, Card, Field, inputClass } from "@/components/ui/primitives";
import { post } from "@/lib/api";
import { setSession, type Session } from "@/lib/session";
import { useCompanies, useHealth } from "@/services/queries";

const schema = z.object({ username: z.string().trim().min(2, "Enter your company username"), password: z.string().min(1, "Enter your password") });
type Values = z.infer<typeof schema>;

export default function Login() {
  const navigate = useNavigate();
  const [sp] = useSearchParams();
  const health = useHealth();
  const companies = useCompanies(true);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) });
  const onSubmit = async (v: Values) => {
    setError(null);
    try {
      const s = await post<Session>("/api/auth/login", v);
      setSession(s);
      navigate(`/app/${s.company.id}/focus`);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const openDemo = async (id: number) => {
    try {
      await demoLogin(id);
      navigate(`/app/${id}/focus`);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-950 px-4">
      <Card className="w-full max-w-md p-8">
        <Link to="/" className="flex items-center gap-2.5"><Logo /><span className="font-semibold text-ink">Virtual Science Park</span></Link>
        <h1 className="mt-6 text-xl font-semibold text-ink">Sign in to your company workspace</h1>
        <p className="mt-1 text-[13px] text-ink-3">One login per company. Profile edits, priorities and saved items stay private to your company.</p>
        {sp.get("company") && <p className="mt-3 rounded-lg bg-amber-50 p-2.5 text-[12.5px] text-amber-900">Please sign in to open that workspace.</p>}
        <form onSubmit={handleSubmit(onSubmit)} className="mt-5 space-y-3" noValidate>
          <Field label="Username (company)"><input {...register("username")} autoComplete="username" className={inputClass} placeholder="e.g. ocean-harvesting" /></Field>
          {errors.username && <p role="alert" className="text-[12.5px] text-critical">{errors.username.message}</p>}
          <Field label="Password"><input type="password" {...register("password")} autoComplete="current-password" className={inputClass} /></Field>
          {errors.password && <p role="alert" className="text-[12.5px] text-critical">{errors.password.message}</p>}
          {error && <p role="alert" className="text-[12.5px] text-critical">{error}</p>}
          <Button type="submit" className="w-full" loading={isSubmitting}>Sign in</Button>
        </form>
        {health.data?.demo_mode && (
          <div className="mt-6 border-t border-line pt-5">
            <p className="text-[12.5px] font-medium text-ink-2">Demo mode — open a demonstration workspace</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {companies.data?.items.filter((c) => c.is_demo_company).map((c) => <Button key={c.id} size="sm" variant="outline" onClick={() => openDemo(c.id)}>{c.name}</Button>)}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
