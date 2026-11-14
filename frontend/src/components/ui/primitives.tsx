import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Inbox, Loader2, RefreshCw, X } from "lucide-react";
import { forwardRef, useEffect, useId, useRef, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "outline" | "danger" | "subtle";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-600 shadow-sm",
  secondary: "bg-navy-900 text-white hover:bg-navy-800",
  outline: "border border-line-2 bg-white text-ink hover:bg-canvas",
  ghost: "text-ink-2 hover:bg-canvas hover:text-ink",
  subtle: "bg-brand-50 text-brand-600 hover:bg-brand-100",
  danger: "bg-critical text-white hover:opacity-90",
};
const sizes: Record<Size, string> = { sm: "h-8 px-3 text-[13px]", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-[15px]" };

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, icon, className, children, disabled, ...rest }, ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant], sizes[size], className,
      )}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
});

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-line bg-surface shadow-[var(--shadow-card)]", className)} {...rest} />;
}

export function CardHeader({ title, subtitle, action, icon, className }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode; icon?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex items-start justify-between gap-4 px-5 pt-5", className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon && <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand">{icon}</div>}
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold text-ink">{title}</h3>
          {subtitle && <p className="mt-0.5 text-[13px] text-ink-3">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5", className)} {...rest} />;
}

const tones = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  brand: "bg-brand-50 text-brand-600 ring-brand-100",
  teal: "bg-teal-50 text-teal ring-teal-300/40",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  amber: "bg-amber-50 text-amber-800 ring-amber-200",
  red: "bg-red-50 text-red-700 ring-red-200",
  violet: "bg-violet-50 text-violet-700 ring-violet-200",
  navy: "bg-navy-900 text-white ring-navy-700",
} as const;
export type Tone = keyof typeof tones;

export function Badge({ tone = "neutral", className, icon, children, title }: { tone?: Tone; className?: string; icon?: ReactNode; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[12px] font-medium ring-1 ring-inset", tones[tone], className)}>
      {icon}
      {children}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-lg bg-slate-200/70", className)} aria-hidden />;
}

export function LoadingBlock({ rows = 3, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

export function EmptyState({ title, description, action, icon }: { title: string; description?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line-2 bg-white/60 px-6 py-12 text-center">
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-canvas text-ink-3">{icon ?? <Inbox className="size-5" />}</div>
      <p className="font-medium text-ink">{title}</p>
      {description && <p className="mt-1 max-w-md text-[13px] text-ink-3">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "Something went wrong" }: { error: unknown; onRetry?: () => void; title?: string }) {
  const message = error instanceof Error ? error.message : "Unexpected error";
  return (
    <div role="alert" className="flex flex-col items-center rounded-2xl border border-red-200 bg-red-50/60 px-6 py-10 text-center">
      <AlertTriangle className="mb-2 size-6 text-critical" aria-hidden />
      <p className="font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-md text-[13px] text-ink-2">{message}</p>
      {onRetry && <Button variant="outline" size="sm" className="mt-4" icon={<RefreshCw className="size-4" />} onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1.5 text-[12px] font-semibold uppercase tracking-wider text-brand">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-ink md:text-[28px]">{title}</h1>
        {description && <p className="mt-1.5 max-w-3xl text-[14px] leading-relaxed text-ink-3">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, items, className, label }: { value: T; onChange: (v: T) => void; items: { value: T; label: ReactNode; count?: number }[]; className?: string; label: string }) {
  return (
    <div role="tablist" aria-label={label} className={cn("inline-flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1", className)}>
      {items.map((it) => (
        <button
          key={it.value}
          role="tab"
          aria-selected={value === it.value}
          onClick={() => onChange(it.value)}
          className={cn("rounded-lg px-3 py-1.5 text-[13px] font-medium transition", value === it.value ? "bg-white text-ink shadow-sm" : "text-ink-3 hover:text-ink")}
        >
          {it.label}
          {it.count !== undefined && <span className="ml-1.5 text-ink-3">{it.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Drawer({ open, onClose, title, children, width = "max-w-2xl" }: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; width?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50">
          <motion.div className="absolute inset-0 bg-navy-950/40 backdrop-blur-[2px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            ref={ref}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className={cn("absolute inset-y-0 right-0 flex w-full flex-col bg-white shadow-2xl outline-none", width)}
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 40, opacity: 0 }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
          >
            <div className="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
              <h2 id={titleId} className="text-[17px] font-semibold leading-snug text-ink">{title}</h2>
              <button onClick={onClose} aria-label="Close panel" className="rounded-lg p-1.5 text-ink-3 hover:bg-canvas hover:text-ink"><X className="size-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-ink-2">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[12px] text-ink-3">{hint}</span>}
    </label>
  );
}

export const inputClass = "h-10 w-full rounded-lg border border-line-2 bg-white px-3 text-sm text-ink placeholder:text-ink-3 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20";

export function Stat({ label, value, hint, icon }: { label: string; value: ReactNode; hint?: ReactNode; icon?: ReactNode }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between text-[12px] font-medium text-ink-3">
        <span>{label}</span>
        {icon}
      </div>
      <div className="mt-2 text-[26px] font-semibold tracking-tight text-ink">{value}</div>
      {hint && <div className="mt-0.5 text-[12px] text-ink-3">{hint}</div>}
    </Card>
  );
}
