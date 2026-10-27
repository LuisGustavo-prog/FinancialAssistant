import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import { EmptyState, ErrorState, PageTitle } from "@/components/StateViews";
import { useEntryForms } from "@/components/EntryForms";

export const Route = createFileRoute("/transactions")({
  head: () => ({
    meta: [
      { name: "description", content: "Gastos e rendas extras do mês atual." },
      { property: "og:description", content: "Gastos e rendas extras do mês atual." },
    ],
  }),
  component: TransactionsPage,
});

function TransactionsPage() {
  return (
    <div className="space-y-6">
      <PageTitle>Lançamentos</PageTitle>
      <Tabs defaultValue="expenses">
        <TabsList className="grid h-11 w-full grid-cols-2">
          <TabsTrigger value="expenses" className="h-9">
            Gastos
          </TabsTrigger>
          <TabsTrigger value="incomes" className="h-9">
            Rendas extras
          </TabsTrigger>
        </TabsList>
        <TabsContent value="expenses" className="mt-4">
          <ExpensesTab />
        </TabsContent>
        <TabsContent value="incomes" className="mt-4">
          <IncomesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Carregando">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-16 w-full rounded-xl" />
      ))}
    </div>
  );
}

const ALL = "all";

function ExpensesTab() {
  const { openExpense } = useEntryForms();
  const expenses = useQuery({ queryKey: ["expenses"], queryFn: api.getExpenses });
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.getCategories });
  const [filter, setFilter] = useState(ALL);

  const newButton = (
    <Button className="h-11 gap-2" onClick={() => openExpense()}>
      <Plus className="h-4 w-4" aria-hidden /> Novo gasto
    </Button>
  );

  if (expenses.isError)
    return <ErrorState error={expenses.error} onRetry={() => expenses.refetch()} />;
  if (!expenses.data) return <ListSkeleton />;
  if (expenses.data.length === 0)
    return <EmptyState text="Nenhum gasto neste mês ainda." action={newButton} />;

  const rows =
    filter === ALL ? expenses.data : expenses.data.filter((e) => String(e.category.id) === filter);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="grid gap-2 sm:w-64">
          <Label htmlFor="category-filter">Categoria</Label>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger id="category-filter" className="h-11">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL} className="min-h-11">
                Todas
              </SelectItem>
              {(categories.data ?? []).map((c) => (
                <SelectItem key={c.id} value={String(c.id)} className="min-h-11">
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {newButton}
      </div>

      {rows.length === 0 ? (
        <EmptyState
          text="Nenhum gasto nesta categoria."
          action={
            <Button variant="outline" className="h-11" onClick={() => setFilter(ALL)}>
              Mostrar todos
            </Button>
          }
        />
      ) : (
        <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-soft">
          {rows.map((e) => (
            <li key={e.id} className="border-t border-border first:border-t-0">
              <button
                type="button"
                onClick={() => openExpense(e)}
                className="flex min-h-14 w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent"
              >
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
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function IncomesTab() {
  const { openIncome } = useEntryForms();
  const incomes = useQuery({ queryKey: ["extra_incomes"], queryFn: api.getExtraIncomes });

  const newButton = (
    <Button className="h-11 gap-2" onClick={() => openIncome()}>
      <Plus className="h-4 w-4" aria-hidden /> Nova renda extra
    </Button>
  );

  if (incomes.isError)
    return <ErrorState error={incomes.error} onRetry={() => incomes.refetch()} />;
  if (!incomes.data) return <ListSkeleton />;
  if (incomes.data.length === 0)
    return <EmptyState text="Nenhuma renda extra neste mês." action={newButton} />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">{newButton}</div>
      <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-soft">
        {incomes.data.map((i) => {
          const content = (
            <>
              <div className="min-w-0 flex-1">
                <p
                  className={`truncate text-sm font-medium ${i.description ? "" : "text-muted-foreground"}`}
                >
                  {i.description ?? "Sem descrição"}
                </p>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                  {i.source === "leftover" && (
                    <Badge variant="secondary" className="font-normal">
                      Sobra do mês anterior
                    </Badge>
                  )}
                  <span className="tabular-nums">{formatDate(i.occurred_on)}</span>
                </div>
              </div>
              <span className="text-sm font-medium tabular-nums text-success">
                + {formatMoney(i.amount)}
              </span>
            </>
          );
          return (
            <li key={i.id} className="border-t border-border first:border-t-0">
              {i.is_editable === false ? (
                <div className="flex min-h-14 items-center gap-3 px-4 py-3">{content}</div>
              ) : (
                <button
                  type="button"
                  onClick={() => openIncome(i)}
                  className="flex min-h-14 w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent"
                >
                  {content}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
