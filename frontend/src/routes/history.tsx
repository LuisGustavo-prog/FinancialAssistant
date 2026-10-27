import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDate, formatMoney, formatMonthYear } from "@/lib/format";
import { EmptyState, ErrorState, PageTitle } from "@/components/StateViews";
import type { MonthDetail, MonthItem } from "@/lib/types";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { name: "description", content: "Meses fechados do seu controle de gastos." },
      { property: "og:description", content: "Meses fechados do seu controle de gastos." },
    ],
  }),
  component: HistoryPage,
});

function balanceBadge(finalBalance: number) {
  if (finalBalance > 0)
    return (
      <Badge variant="outline" className="border-success/50 font-normal text-success">
        Sobra
      </Badge>
    );
  if (finalBalance < 0)
    return (
      <Badge variant="outline" className="border-destructive/50 font-normal text-destructive">
        Negativo
      </Badge>
    );
  return (
    <Badge variant="secondary" className="font-normal">
      Zerado
    </Badge>
  );
}

function HistoryPage() {
  const months = useQuery({ queryKey: ["months"], queryFn: api.getMonths });
  const [selected, setSelected] = useState<number | null>(null);

  if (selected !== null) return <MonthDetailView id={selected} onBack={() => setSelected(null)} />;

  let body: React.ReactNode;
  const data = months.data as MonthItem[] | undefined;
  if (months.isError) {
    body = <ErrorState error={months.error} onRetry={() => months.refetch()} />;
  } else if (!data) {
    body = (
      <div className="space-y-2" aria-busy="true" aria-label="Carregando">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  } else if (data.length === 0) {
    body = <EmptyState text="Nenhum mês fechado ainda." />;
  } else {
    body = (
      <>
        <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-soft">
          {data.map((m) => (
            <li key={m.id} className="border-t border-border first:border-t-0">
              <button
                type="button"
                onClick={() => setSelected(m.id)}
                className="flex min-h-14 w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{formatMonthYear(m.year, m.month_number)}</p>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {balanceBadge(m.final_balance)}
                    {m.leftover_decision === "pending" && (
                      <Badge
                        variant="outline"
                        className="border-warning/50 font-normal text-warning"
                      >
                        Sobra pendente
                      </Badge>
                    )}
                  </div>
                </div>
                <span className="text-sm tabular-nums">
                  {m.final_balance > 0 ? "+ " : m.final_balance < 0 ? "- " : ""}
                  {formatMoney(Math.abs(m.final_balance))}
                </span>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground">
          Meses em que o app não foi aberto não aparecem aqui.
        </p>
      </>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle>Histórico</PageTitle>
      {body}
    </div>
  );
}

function MonthDetailView({ id, onBack }: { id: number; onBack: () => void }) {
  const detail = useQuery({ queryKey: ["months", id], queryFn: () => api.getMonth(id) });

  if (detail.isError)
    return (
      <div className="space-y-6">
        <BackButton onBack={onBack} />
        <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
      </div>
    );
  if (!detail.data)
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Carregando">
        <BackButton onBack={onBack} />
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );

  const d = detail.data as MonthDetail;
  const b = d.breakdown;
  const rows = [
    { label: "Salário", value: b.salary, sign: "+" },
    { label: "Rendas extras", value: b.extra_incomes, sign: "+" },
    { label: "Gastos fixos", value: b.fixed_expenses, sign: "-" },
    { label: "Cotas de poupança", value: b.savings_quotas, sign: "-" },
    { label: "Gastos no débito", value: b.debit_expenses, sign: "-" },
    { label: "Cartão de crédito", value: b.credit_card_total, sign: "-" },
  ] as const;

  return (
    <div className="space-y-6">
      <BackButton onBack={onBack} />
      <PageTitle>{formatMonthYear(d.year, d.month_number)}</PageTitle>

      <section className="rounded-xl border border-border bg-card shadow-soft">
        <h2 className="px-5 pb-2 pt-5 font-semibold">De onde vem esse valor</h2>
        <ul>
          {rows.map((r) => (
            <li
              key={r.label}
              className="flex min-h-12 items-center gap-3 border-t border-border px-5 py-2 first:border-t-0"
            >
              <span className="flex-1 text-sm">{r.label}</span>
              <span className="tabular-nums">
                {r.sign} {formatMoney(r.value)}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <DetailSection title="Gastos" empty="Nenhum gasto neste mês." count={d.expenses.length}>
        {d.expenses.map((e) => (
          <li key={e.id} className="flex items-center gap-3 border-t border-border px-5 py-3">
            <div className="min-w-0 flex-1">
              <p
                className={`truncate text-sm font-medium ${e.description ? "" : "text-muted-foreground"}`}
              >
                {e.description ?? "Sem descrição"}
              </p>
              <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="secondary" className="font-normal">
                  {e.category.name}
                </Badge>
                <span className="tabular-nums">{formatDate(e.occurred_on)}</span>
              </div>
            </div>
            <span className="text-sm tabular-nums">- {formatMoney(e.amount)}</span>
          </li>
        ))}
      </DetailSection>

      <DetailSection
        title="Rendas extras"
        empty="Nenhuma renda extra neste mês."
        count={d.extra_incomes.length}
      >
        {d.extra_incomes.map((i) => (
          <li key={i.id} className="flex items-center gap-3 border-t border-border px-5 py-3">
            <div className="min-w-0 flex-1">
              <p
                className={`truncate text-sm font-medium ${i.description ? "" : "text-muted-foreground"}`}
              >
                {i.description ?? "Sem descrição"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                {formatDate(i.occurred_on)}
              </p>
            </div>
            <span className="text-sm font-medium tabular-nums text-success">
              + {formatMoney(i.amount)}
            </span>
          </li>
        ))}
      </DetailSection>

      <DetailSection
        title="Gastos fixos"
        empty="Nenhum gasto fixo neste mês."
        count={d.fixed_expenses.length}
      >
        {d.fixed_expenses.map((f, idx) => (
          <li key={idx} className="flex items-center gap-3 border-t border-border px-5 py-3">
            <span className="flex-1 text-sm">{f.name}</span>
            <span className="text-sm tabular-nums">- {formatMoney(f.amount)}</span>
          </li>
        ))}
      </DetailSection>

      <DetailSection
        title="Cotas de poupança"
        empty="Nenhuma cota de poupança neste mês."
        count={d.savings_quotas.length}
      >
        {d.savings_quotas.map((s, idx) => (
          <li key={idx} className="flex items-center gap-3 border-t border-border px-5 py-3">
            <span className="flex-1 text-sm">{s.name}</span>
            <span className="text-sm tabular-nums">- {formatMoney(s.amount)}</span>
          </li>
        ))}
      </DetailSection>

      <DetailSection title="Cartões" empty="Nenhum cartão neste mês." count={d.credit_cards.length}>
        {d.credit_cards.map((c) => (
          <li key={c.id} className="flex items-center gap-3 border-t border-border px-5 py-3">
            <span className="flex-1 text-sm">{c.name}</span>
            <span className="text-sm tabular-nums">- {formatMoney(c.total)}</span>
          </li>
        ))}
      </DetailSection>
    </div>
  );
}

function BackButton({ onBack }: { onBack: () => void }) {
  return (
    <Button variant="ghost" className="h-11 gap-1 px-2" onClick={onBack}>
      <ChevronLeft className="h-4 w-4" aria-hidden /> Voltar
    </Button>
  );
}

function DetailSection({
  title,
  empty,
  count,
  children,
}: {
  title: string;
  empty: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card shadow-soft">
      <h2 className="px-5 pb-2 pt-5 font-semibold">{title}</h2>
      {count === 0 ? (
        <p className="px-5 pb-5 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul>{children}</ul>
      )}
    </section>
  );
}
