import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, Plus } from "lucide-react";
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatMoney, parseMoneyInput } from "@/lib/format";
import { EmptyState, ErrorState, PageTitle, errorMessage } from "@/components/StateViews";
import type { CardEntry, CreditCard } from "@/lib/types";

export const Route = createFileRoute("/credit-cards")({
  head: () => ({
    meta: [
      { name: "description", content: "Cartão do seu controle de gastos mensais." },
      { property: "og:description", content: "Cartão do seu controle de gastos mensais." },
    ],
  }),
  component: CreditCardsPage,
});

function toInput(n: number): string {
  return n.toFixed(2).replace(".", ",");
}

function CreditCardsPage() {
  const cards = useQuery({ queryKey: ["credit_cards"], queryFn: api.getCreditCards });
  const [createOpen, setCreateOpen] = useState(false);

  const createButton = (
    <Button className="h-11 gap-2" onClick={() => setCreateOpen(true)}>
      <Plus className="h-4 w-4" aria-hidden /> Cadastrar cartão
    </Button>
  );

  let body: React.ReactNode;
  if (cards.isError) {
    body = <ErrorState error={cards.error} onRetry={() => cards.refetch()} />;
  } else if (!cards.data) {
    body = (
      <div className="space-y-2" aria-busy="true" aria-label="Carregando">
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  } else {
    const visible = cards.data.filter((c) => c.in_current_month);
    if (visible.length === 0) {
      body = <EmptyState text="Você ainda não cadastrou nenhum cartão." action={createButton} />;
    } else if (visible.length === 1) {
      body = <CardView key={visible[0]!.id} card={visible[0]!} />;
    } else {
      body = (
        <Tabs defaultValue={String(visible[0]!.id)}>
          <TabsList className="h-11 w-full">
            {visible.map((c) => (
              <TabsTrigger key={c.id} value={String(c.id)} className="h-9 flex-1">
                {c.name}
              </TabsTrigger>
            ))}
          </TabsList>
          {visible.map((c) => (
            <TabsContent key={c.id} value={String(c.id)} className="mt-4">
              <CardView card={c} />
            </TabsContent>
          ))}
        </Tabs>
      );
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <PageTitle>Cartão</PageTitle>
        {cards.data && cards.data.some((c) => c.in_current_month) && createButton}
      </div>
      {body}
      <CreateCardDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}

function CardView({ card }: { card: CreditCard }) {
  const qc = useQueryClient();
  const [reported, setReported] = useState(toInput(card.reported_value ?? 0));
  const [reportedError, setReportedError] = useState<string | null>(null);
  const [decreased, setDecreased] = useState<string | null>(null);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [editing, setEditing] = useState<CardEntry | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setReported(toInput(card.reported_value ?? 0));
  }, [card.reported_value]);

  async function refresh() {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["credit_cards"] }),
      qc.invalidateQueries({ queryKey: ["home"] }),
    ]);
  }

  async function submitReported(type?: "payment" | "refund") {
    const value = parseMoneyInput(reported);
    if (Number.isNaN(value)) {
      setReportedError("Digite um valor, por exemplo 815,04.");
      return;
    }
    setSaving(true);
    setReportedError(null);
    try {
      await api.updateReportedValue(card.id, value, type);
      await refresh();
      setDecreased(null);
    } catch (e) {
      if (e instanceof ApiError && e.code === "value_decreased") setDecreased(e.message);
      else setReportedError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  const updatedLabel =
    card.days_since_update === null
      ? "Ainda não atualizado neste mês"
      : card.days_since_update === 0
        ? "Atualizado hoje"
        : `Atualizado há ${card.days_since_update} ${card.days_since_update === 1 ? "dia" : "dias"}`;
  const outdated = card.is_outdated;

  return (
    <section className="space-y-6 rounded-xl border border-border bg-card p-5 shadow-soft">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">{card.name}</h2>
          {!card.is_active && (
            <Badge variant="outline" className="border-warning/50 font-normal text-warning">
              Desativado: sai no próximo mês
            </Badge>
          )}
        </div>
        {card.total !== null && (
          <p className="text-3xl font-semibold tabular-nums">{formatMoney(card.total)}</p>
        )}
        {card.reported_value !== null && card.payments_total !== null && card.total !== null && (
          <p className="text-sm text-muted-foreground tabular-nums">
            {formatMoney(card.reported_value)} + {formatMoney(card.payments_total)} ={" "}
            {formatMoney(card.total)}
          </p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor={`reported-${card.id}`}>Valor informado</Label>
        <div className="flex gap-2">
          <Input
            id={`reported-${card.id}`}
            inputMode="decimal"
            placeholder="0,00"
            value={reported}
            onChange={(e) => setReported(e.target.value)}
            className="h-11 tabular-nums"
            aria-invalid={!!reportedError}
          />
          <Button className="h-11" disabled={saving} onClick={() => void submitReported()}>
            Atualizar
          </Button>
        </div>
        {reportedError && <p className="text-sm text-destructive">{reportedError}</p>}
        <div>
          <Badge
            variant="outline"
            className={
              outdated
                ? "border-warning/50 font-normal text-warning"
                : "font-normal text-muted-foreground"
            }
          >
            {updatedLabel}
          </Badge>
        </div>
      </div>

      <p className="flex gap-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>
          Copie sempre a mesma fatura do banco, a que o banco chama pelo nome do mês. Alternar entre
          a fatura fechada e a aberta pode contar um valor duas vezes ou pular um valor.
        </span>
      </p>

      <Button variant="outline" className="h-11 w-full" onClick={() => setPaymentOpen(true)}>
        Registrar pagamento
      </Button>

      <div className="space-y-3">
        <h3 className="text-sm font-medium">Pagamentos e estornos do mês</h3>
        <p className="text-sm text-muted-foreground">
          Pagamentos contam no total do mês. Estornos não contam, e o total diminui.
        </p>
        {card.entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum pagamento ou estorno neste mês.</p>
        ) : (
          <ul className="overflow-hidden rounded-xl border border-border">
            {card.entries.map((entry) => (
              <li key={entry.id} className="border-t border-border first:border-t-0">
                <button
                  type="button"
                  onClick={() => setEditing(entry)}
                  className="flex min-h-14 w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent"
                >
                  <div className="min-w-0 flex-1">
                    <Badge variant="secondary" className="font-normal">
                      {entry.type === "refund" ? "Estorno" : "Pagamento"}
                    </Badge>
                    <span className="ml-2 text-xs text-muted-foreground tabular-nums">
                      {formatDate(entry.occurred_on)}
                    </span>
                  </div>
                  <span className="text-sm tabular-nums">{formatMoney(entry.amount)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <PaymentDialog
        card={card}
        open={paymentOpen}
        onOpenChange={setPaymentOpen}
        onDone={refresh}
      />

      <AlertDialog open={decreased !== null} onOpenChange={(o) => !o && setDecreased(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Valor diminuiu</AlertDialogTitle>
            <AlertDialogDescription>{decreased}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="h-11">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="h-11"
              disabled={saving}
              onClick={(e) => {
                e.preventDefault();
                void submitReported("refund");
              }}
            >
              Estorno
            </AlertDialogAction>
            <AlertDialogAction
              className="h-11"
              disabled={saving}
              onClick={(e) => {
                e.preventDefault();
                void submitReported("payment");
              }}
            >
              Pagamento
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {editing && (
        <EntryEditDialog
          key={editing.id}
          entry={editing}
          onClose={() => setEditing(null)}
          onDone={refresh}
        />
      )}
    </section>
  );
}

function PaymentDialog({
  card,
  open,
  onOpenChange,
  onDone,
}: {
  card: CreditCard;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onDone: () => Promise<void>;
}) {
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setAmount(toInput(card.reported_value ?? 0));
      setError(null);
    }
  }, [open, card.reported_value]);

  async function confirm() {
    const value = parseMoneyInput(amount);
    if (Number.isNaN(value)) {
      setError("Digite um valor, por exemplo 200,00.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.registerPayment(card.id, value);
      await onDone();
      onOpenChange(false);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Registrar pagamento</DialogTitle>
          <DialogDescription className="sr-only">
            Informe o valor pago na fatura deste mês.
          </DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void confirm();
          }}
        >
          <div className="grid gap-2">
            <Label htmlFor="payment-amount">Valor</Label>
            <Input
              id="payment-amount"
              autoFocus
              inputMode="decimal"
              placeholder="0,00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
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
            {saving ? "Salvando…" : "Confirmar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EntryEditDialog({
  entry,
  onClose,
  onDone,
}: {
  entry: CardEntry;
  onClose: () => void;
  onDone: () => Promise<void>;
}) {
  const [amount, setAmount] = useState(toInput(entry.amount));
  const [date, setDate] = useState(entry.occurred_on);
  const [type, setType] = useState(entry.type === "refund" ? "refund" : "payment");
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving, setSaving] = useState(false);

  async function save() {
    const value = parseMoneyInput(amount);
    if (Number.isNaN(value)) {
      setError("Digite um valor, por exemplo 200,00.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateCardEntry(entry.id, { amount: value, occurred_on: date, type });
      await onDone();
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    setSaving(true);
    setError(null);
    try {
      await api.deleteCardEntry(entry.id);
      await onDone();
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
      setConfirmDelete(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar lançamento do cartão</DialogTitle>
          <DialogDescription className="sr-only">
            Altere o valor, a data ou o tipo do lançamento.
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
            <Label htmlFor="entry-edit-amount">Valor</Label>
            <Input
              id="entry-edit-amount"
              autoFocus
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="h-11 tabular-nums"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="entry-edit-date">Data</Label>
            <Input
              id="entry-edit-date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="h-11"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="entry-edit-type">Tipo</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger id="entry-edit-type" className="h-11">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="payment" className="min-h-11">
                  Pagamento
                </SelectItem>
                <SelectItem value="refund" className="min-h-11">
                  Estorno
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
            <Button
              type="button"
              variant="outline"
              className="h-11 text-destructive"
              disabled={saving}
              onClick={() => setConfirmDelete(true)}
            >
              Apagar
            </Button>
            <Button type="submit" className="h-11" disabled={saving}>
              {saving ? "Salvando…" : "Salvar"}
            </Button>
          </div>
        </form>

        <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Apagar este lançamento?</AlertDialogTitle>
              <AlertDialogDescription>Essa ação não pode ser desfeita.</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="h-11">Cancelar</AlertDialogCancel>
              <AlertDialogAction
                className="h-11 bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={remove}
              >
                Apagar
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </DialogContent>
    </Dialog>
  );
}

function CreateCardDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setName("");
      setError(null);
    }
  }, [open]);

  async function save() {
    if (!name.trim()) {
      setError("Digite o nome do cartão.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.createCreditCard({ name: name.trim() });
      await qc.invalidateQueries({ queryKey: ["credit_cards"] });
      onOpenChange(false);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cadastrar cartão</DialogTitle>
          <DialogDescription className="sr-only">Informe o nome do cartão.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <div className="grid gap-2">
            <Label htmlFor="card-name">Nome</Label>
            <Input
              id="card-name"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-11"
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" className="h-11" disabled={saving}>
            {saving ? "Salvando…" : "Cadastrar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
