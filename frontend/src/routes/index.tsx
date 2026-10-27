import { useEffect, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { daysLeftLabel, formatDate, formatMoney, formatMonthYear } from "@/lib/format";
import { EmptyState, ErrorState, errorMessage } from "@/components/StateViews";
import type { HomeOk, Notice } from "@/lib/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { name: "description", content: "Seu saldo livre do mês e os últimos gastos." },
      { property: "og:description", content: "Seu saldo livre do mês e os últimos gastos." },
    ],
  }),
  component: HomePage,
});

const NOTICE_STYLE: Record<string, { container: string; dot: string }> = {
  month_ending: { container: "border-warning/25 bg-warning/[0.06]", dot: "bg-warning" },
  credit_card_not_updated: { container: "border-warning/25 bg-warning/[0.06]", dot: "bg-warning" },
  month_closed_negative: {
    container: "border-destructive/25 bg-destructive/[0.06]",
    dot: "bg-destructive",
  },
  unused_months: { container: "border-border bg-muted", dot: "bg-muted-foreground/50" },
};

function HomePage() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["home"], queryFn: api.getHome, retry: false });

  useEffect(() => {
    if (query.data?.status === "needs_setup") navigate({ to: "/setup" });
  }, [query.data, navigate]);

  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (!query.data || query.data.status !== "ok") return <HomeSkeleton />;
  return <HomeContent home={query.data} refetch={() => query.refetch()} />;
}

function HomeContent({ home, refetch }: { home: HomeOk; refetch: () => Promise<unknown> }) {
  const [hidden, setHidden] = useState<Set<Notice>>(new Set());
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setActionError(null);
    try {
      await fn();
      await refetch();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  function dismiss(n: Notice) {
    if (n.id === null) setHidden((s) => new Set(s).add(n));
    else void run(() => api.dismissNotice(n.id as number));
  }

  const b = home.breakdown;
  const fb = home.free_balance;
  const balanceColor = fb > 0 ? "text-success" : fb < 0 ? "text-destructive" : "text-foreground";

  const rows = [
    { label: "Salário", value: b.salary, sign: "+", to: "/registry" },
    { label: "Rendas extras", value: b.extra_incomes, sign: "+", to: "/transactions" },
    { label: "Gastos fixos", value: b.fixed_expenses, sign: "-", to: "/registry" },
    { label: "Cotas de poupança", value: b.savings_quotas, sign: "-", to: "/registry" },
    { label: "Gastos no débito", value: b.debit_expenses, sign: "-", to: "/transactions" },
    { label: "Cartão de crédito", value: b.credit_card_total, sign: "-", to: "/credit-cards" },
  ] as const;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">
          {formatMonthYear(home.month.year, home.month.month_number)}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">{daysLeftLabel(home.month.days_left)}</p>
      </header>

      {actionError && (
        <div
          role="alert"
          className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm"
        >
          <span className="font-medium">Erro: </span>
          {actionError}
        </div>
      )}

      {home.notices.filter((n) => !hidden.has(n)).length > 0 && (
        <div className="space-y-2">
          {home.notices
            .filter((n) => !hidden.has(n))
            .map((n, i) => {
              const style = NOTICE_STYLE[n.code] ?? {
                container: "border-border bg-card",
                dot: "bg-muted-foreground/50",
              };
              return (
                <div
                  key={n.id ?? `${n.code}-${i}`}
                  className={`flex items-start gap-3 rounded-xl border p-3 pl-4 shadow-soft ${style.container}`}
                >
                  <span
                    className={`mt-[9px] h-2 w-2 shrink-0 rounded-full ${style.dot}`}
                    aria-hidden
                  />
                  <p className="flex-1 py-1.5 text-sm">{n.message}</p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Dispensar aviso"
                    disabled={busy}
                    onClick={() => dismiss(n)}
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-background/60"
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              );
            })}
        </div>
      )}

      {home.pending_leftover && (
        <section className="rounded-xl border border-success/30 bg-success/[0.04] p-5 shadow-soft">
          <div className="flex items-start gap-3">
            <span className="mt-[7px] h-2 w-2 shrink-0 rounded-full bg-success" aria-hidden />
            <p className="flex-1">{home.pending_leftover.message}</p>
          </div>
          <div className="mt-4 flex gap-2">
            <Button
              className="h-11 flex-1"
              disabled={busy}
              onClick={() => {
                const pending = home.pending_leftover;
                if (pending) void run(() => api.decideLeftover(pending.month_id, "carried"));
              }}
            >
              Levar
            </Button>
            <Button
              variant="outline"
              className="h-11 flex-1 bg-background"
              disabled={busy}
              onClick={() => {
                const pending = home.pending_leftover;
                if (pending) void run(() => api.decideLeftover(pending.month_id, "declined"));
              }}
            >
              Não levar
            </Button>
          </div>
        </section>
      )}

      <section className="border-y border-border py-8">
        <p className="text-sm font-medium text-muted-foreground">Saldo livre</p>
        <p className={`mt-3 text-4xl font-medium tabular-nums sm:text-5xl ${balanceColor}`}>
          {formatMoney(fb)}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Você ainda pode gastar este valor no mês
        </p>
      </section>

      <section>
        <h2 className="pb-4 font-semibold">De onde vem esse valor</h2>
        <ul>
          {rows.map((r) => (
            <li key={r.label} className="border-t border-border first:border-t-0">
              <Link
                to={r.to}
                className="flex min-h-14 items-center gap-3 py-2 transition-colors hover:bg-accent"
              >
                <span className="flex-1 text-sm">{r.label}</span>
                <span className="tabular-nums">
                  {r.sign} {formatMoney(r.value)}
                </span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <div className="flex items-center justify-between pb-3">
          <h2 className="font-semibold">Últimos gastos</h2>
          <Link
            to="/transactions"
            className="flex min-h-11 items-center text-sm font-medium text-primary"
          >
            Ver todos
          </Link>
        </div>
        {home.recent_expenses.length === 0 ? (
          <div>
            <EmptyState
              text="Nenhum gasto lançado neste mês."
              action={
                <Button asChild className="h-11">
                  <Link to="/transactions">Lançar um gasto</Link>
                </Button>
              }
            />
          </div>
        ) : (
          <ul>
            {home.recent_expenses.map((e) => (
              <li key={e.id} className="flex items-center gap-3 border-t border-border py-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{e.description ?? "Sem descrição"}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="secondary" className="font-normal">
                      {e.category.name}
                    </Badge>
                    <span className="tabular-nums">{formatDate(e.occurred_on)}</span>
                  </div>
                </div>
                <span className="tabular-nums text-sm">- {formatMoney(e.amount)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Carregando">
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-24" />
      </div>
      <Skeleton className="h-36 w-full rounded-xl" />
      <Skeleton className="h-72 w-full rounded-xl" />
      <Skeleton className="h-48 w-full rounded-xl" />
    </div>
  );
}
