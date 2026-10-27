import { useEffect, useState, type ReactNode } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { formatMoney, parseMoneyInput } from "@/lib/format";
import { EmptyState, ErrorState, PageTitle, errorMessage } from "@/components/StateViews";

export const Route = createFileRoute("/registry")({
  head: () => ({
    meta: [
      {
        name: "description",
        content: "Salário, gastos fixos, cotas de poupança, categorias e cartões.",
      },
      {
        property: "og:description",
        content: "Salário, gastos fixos, cotas de poupança, categorias e cartões.",
      },
    ],
  }),
  component: RegistryPage,
});

function RegistryPage() {
  return (
    <div className="space-y-6">
      <PageTitle>Cadastros</PageTitle>
      <Tabs defaultValue="salary">
        <TabsList className="flex h-auto w-full flex-wrap">
          <TabsTrigger value="salary" className="h-9 flex-1">
            Salário
          </TabsTrigger>
          <TabsTrigger value="fixed" className="h-9 flex-1">
            Gastos fixos
          </TabsTrigger>
          <TabsTrigger value="savings" className="h-9 flex-1">
            Cotas de poupança
          </TabsTrigger>
          <TabsTrigger value="categories" className="h-9 flex-1">
            Categorias
          </TabsTrigger>
          <TabsTrigger value="cards" className="h-9 flex-1">
            Cartões
          </TabsTrigger>
        </TabsList>
        <TabsContent value="salary" className="mt-4">
          <SalaryTab />
        </TabsContent>
        <TabsContent value="fixed" className="mt-4">
          <ItemsTab
            queryKey={["fixed_expenses"]}
            queryFn={api.getFixedExpenses}
            createFn={(b) => api.createFixedExpense(b)}
            updateFn={(id, b) => api.updateFixedExpense(id, b)}
            hasAmount
            addLabel="Adicionar gasto fixo"
            editLabel="Alterar"
            emptyText="Nenhum gasto fixo cadastrado. Eles são opcionais."
          />
        </TabsContent>
        <TabsContent value="savings" className="mt-4">
          <ItemsTab
            queryKey={["savings_quotas"]}
            queryFn={api.getSavingsQuotas}
            createFn={(b) => api.createSavingsQuota(b)}
            updateFn={(id, b) => api.updateSavingsQuota(id, b)}
            hasAmount
            addLabel="Adicionar cota de poupança"
            editLabel="Alterar"
            emptyText="Nenhuma cota de poupança cadastrada."
          />
        </TabsContent>
        <TabsContent value="categories" className="mt-4">
          <ItemsTab
            queryKey={["categories"]}
            queryFn={api.getCategories}
            createFn={(b) => api.createCategory(b)}
            updateFn={(id, b) => api.updateCategory(id, b)}
            addLabel="Adicionar categoria"
            editLabel="Renomear"
            emptyText="Nenhuma categoria cadastrada."
            itemBadge={(item) =>
              item.is_default ? (
                <Badge variant="secondary" className="font-normal">
                  Padrão
                </Badge>
              ) : null
            }
            canToggle={(item) => !item.is_default}
          />
        </TabsContent>
        <TabsContent value="cards" className="mt-4">
          <ItemsTab
            queryKey={["credit_cards"]}
            queryFn={api.getCreditCards}
            createFn={(b) => api.createCreditCard(b)}
            updateFn={(id, b) => api.updateCreditCard(id, b)}
            addLabel="Adicionar cartão"
            emptyText="Nenhum cartão cadastrado."
            footerText="Cartões com histórico não são apagados, apenas desativados. Desativar vale a partir do mês seguinte."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ---------------- Salário ---------------- */

function SalaryTab() {
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.getSettings });
  const [editing, setEditing] = useState<"current" | "month" | null>(null);

  if (settings.isError)
    return <ErrorState error={settings.error} onRetry={() => settings.refetch()} />;
  if (!settings.data)
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Carregando">
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );

  const s = settings.data as { current_salary: number; current_month_salary: number };
  return (
    <div className="space-y-4">
      <SalaryBlock
        title="Salário atual"
        value={s.current_salary}
        text="A alteração vale a partir do mês atual. Os meses fechados não mudam."
        onEdit={() => setEditing("current")}
      />
      <SalaryBlock
        title="Salário só deste mês"
        value={s.current_month_salary}
        text="Muda só o mês atual. O salário atual e os meses seguintes não mudam."
        onEdit={() => setEditing("month")}
      />
      {editing && (
        <SalaryDialog
          kind={editing}
          initial={editing === "current" ? s.current_salary : s.current_month_salary}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function SalaryBlock({
  title,
  value,
  text,
  onEdit,
}: {
  title: string;
  value: number;
  text: string;
  onEdit: () => void;
}) {
  return (
    <section className="space-y-3 rounded-xl border border-border bg-card p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold">{title}</h2>
        <Button variant="outline" className="h-11" onClick={onEdit}>
          Alterar
        </Button>
      </div>
      <p className="text-2xl font-semibold tabular-nums">{formatMoney(value)}</p>
      <p className="text-sm text-muted-foreground">{text}</p>
    </section>
  );
}

function SalaryDialog({
  kind,
  initial,
  onClose,
}: {
  kind: "current" | "month";
  initial: number;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [value, setValue] = useState(initial.toFixed(2).replace(".", ","));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save() {
    const v = parseMoneyInput(value);
    if (Number.isNaN(v)) {
      setError("Digite um valor, por exemplo 4500,00.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (kind === "current") await api.saveSettings(v);
      else await api.updateMonthSalary(v);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["settings"] }),
        qc.invalidateQueries({ queryKey: ["home"] }),
      ]);
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {kind === "current" ? "Alterar salário atual" : "Alterar salário só deste mês"}
          </DialogTitle>
          <DialogDescription className="sr-only">
            Informe o novo valor do salário.
          </DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <div className="grid gap-2">
            <Label htmlFor="salary-value">Valor</Label>
            <Input
              id="salary-value"
              autoFocus
              inputMode="decimal"
              placeholder="0,00"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="h-11 tabular-nums"
              aria-invalid={!!error}
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" className="h-11" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ---------------- Listas (gastos fixos, cotas, categorias, cartões) ---------------- */

type RegistryItem = {
  id: number;
  name: string;
  is_active: boolean;
  amount?: number;
  is_default?: boolean;
};

function ItemsTab({
  queryKey,
  queryFn,
  createFn,
  updateFn,
  hasAmount = false,
  addLabel,
  editLabel,
  emptyText,
  footerText,
  itemBadge,
  canToggle,
}: {
  queryKey: string[];
  queryFn: () => Promise<unknown>;
  createFn: (body: Record<string, unknown>) => Promise<unknown>;
  updateFn: (id: number, body: Record<string, unknown>) => Promise<unknown>;
  hasAmount?: boolean;
  addLabel: string;
  editLabel?: string;
  emptyText: string;
  footerText?: string;
  itemBadge?: (item: RegistryItem) => ReactNode;
  canToggle?: (item: RegistryItem) => boolean;
}) {
  const qc = useQueryClient();
  const items = useQuery({ queryKey, queryFn });
  const [dialog, setDialog] = useState<{ item?: RegistryItem } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function refresh() {
    await Promise.all([
      qc.invalidateQueries({ queryKey }),
      qc.invalidateQueries({ queryKey: ["home"] }),
    ]);
  }

  async function toggle(item: RegistryItem) {
    setBusyId(item.id);
    setActionError(null);
    try {
      await updateFn(item.id, { is_active: !item.is_active });
      await refresh();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  }

  if (items.isError) return <ErrorState error={items.error} onRetry={() => items.refetch()} />;
  const data = items.data as RegistryItem[] | undefined;
  if (!data)
    return (
      <div className="space-y-2" aria-busy="true" aria-label="Carregando">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14 w-full rounded-xl" />
        ))}
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button className="h-11 gap-2" onClick={() => setDialog({})}>
          <Plus className="h-4 w-4" aria-hidden /> {addLabel}
        </Button>
      </div>

      {actionError && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm"
        >
          {actionError}
        </p>
      )}

      {data.length === 0 ? (
        <EmptyState text={emptyText} />
      ) : (
        <ul className="overflow-hidden rounded-xl border border-border bg-card shadow-soft">
          {data.map((item) => (
            <li
              key={item.id}
              className={`flex flex-wrap items-center gap-2 border-t border-border px-4 py-3 first:border-t-0 ${
                item.is_active ? "" : "text-muted-foreground"
              }`}
            >
              <span className="min-w-0 flex-1 truncate text-sm font-medium">
                {item.name}
                {itemBadge?.(item) && (
                  <span className="ml-2 inline-block align-middle">{itemBadge(item)}</span>
                )}
              </span>
              {hasAmount && item.amount !== undefined && (
                <span className="text-sm tabular-nums">{formatMoney(item.amount)}</span>
              )}
              {editLabel && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-11"
                  onClick={() => setDialog({ item })}
                >
                  {editLabel}
                </Button>
              )}
              {(canToggle?.(item) ?? true) && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-11"
                  disabled={busyId === item.id}
                  onClick={() => void toggle(item)}
                >
                  {item.is_active ? "Desativar" : "Reativar"}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {footerText && <p className="text-sm text-muted-foreground">{footerText}</p>}

      {dialog && (
        <ItemDialog
          item={dialog.item}
          hasAmount={hasAmount}
          title={dialog.item ? (editLabel ?? "Alterar") : addLabel}
          onClose={() => setDialog(null)}
          onSave={async (body) => {
            if (dialog.item) await updateFn(dialog.item.id, body);
            else await createFn(body);
            await refresh();
          }}
        />
      )}
    </div>
  );
}

function ItemDialog({
  item,
  hasAmount,
  title,
  onClose,
  onSave,
}: {
  item?: RegistryItem | undefined;
  hasAmount: boolean;
  title: string;
  onClose: () => void;
  onSave: (body: Record<string, unknown>) => Promise<void>;
}) {
  const [name, setName] = useState(item?.name ?? "");
  const [amount, setAmount] = useState(
    item?.amount !== undefined ? item.amount.toFixed(2).replace(".", ",") : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(item?.name ?? "");
    setAmount(item?.amount !== undefined ? item.amount.toFixed(2).replace(".", ",") : "");
  }, [item]);

  async function save() {
    if (!name.trim()) {
      setError("Digite o nome.");
      return;
    }
    const body: Record<string, unknown> = { name: name.trim() };
    if (hasAmount) {
      const v = parseMoneyInput(amount);
      if (Number.isNaN(v)) {
        setError("Digite um valor, por exemplo 300,00.");
        return;
      }
      body["amount"] = v;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(body);
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription className="sr-only">Preencha os campos e salve.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <div className="grid gap-2">
            <Label htmlFor="item-name">Nome</Label>
            <Input
              id="item-name"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-11"
            />
          </div>
          {hasAmount && (
            <div className="grid gap-2">
              <Label htmlFor="item-amount">Valor</Label>
              <Input
                id="item-amount"
                inputMode="decimal"
                placeholder="0,00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="h-11 tabular-nums"
              />
            </div>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" className="h-11" disabled={saving}>
            {saving ? "Salvando…" : "Salvar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
