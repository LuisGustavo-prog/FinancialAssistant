import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
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
import { useIsMobile } from "@/hooks/use-mobile";
import { api, ApiError } from "@/lib/api";
import { parseMoneyInput } from "@/lib/format";
import { errorMessage } from "@/components/StateViews";
import type { Expense, ExtraIncome } from "@/lib/types";

type Target =
  | { kind: "expense"; item?: Expense | undefined }
  | { kind: "income"; item?: ExtraIncome | undefined }
  | null;

type Ctx = {
  openExpense: (item?: Expense) => void;
  openIncome: (item?: ExtraIncome) => void;
};

const EntryFormsContext = createContext<Ctx | null>(null);

export function useEntryForms(): Ctx {
  const ctx = useContext(EntryFormsContext);
  if (!ctx) throw new Error("useEntryForms must be used inside EntryFormsProvider");
  return ctx;
}

export function EntryFormsProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<Target>(null);
  const [key, setKey] = useState(0);
  const open = (t: Target) => {
    setKey((k) => k + 1);
    setTarget(t);
  };
  return (
    <EntryFormsContext.Provider
      value={{
        openExpense: (item) => open({ kind: "expense", item }),
        openIncome: (item) => open({ kind: "income", item }),
      }}
    >
      {children}
      <ResponsiveSheet
        open={target !== null}
        onOpenChange={(o) => !o && setTarget(null)}
        title={
          target?.kind === "income"
            ? target.item
              ? "Editar renda extra"
              : "Nova renda extra"
            : target?.item
              ? "Editar gasto"
              : "Novo gasto"
        }
      >
        {target && <EntryForm key={key} target={target} onDone={() => setTarget(null)} />}
      </ResponsiveSheet>
    </EntryFormsContext.Provider>
  );
}

function ResponsiveSheet({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  title: string;
  children: ReactNode;
}) {
  const isMobile = useIsMobile();
  if (isMobile) {
    return (
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent>
          <DrawerHeader className="text-left">
            <DrawerTitle>{title}</DrawerTitle>
            <DrawerDescription className="sr-only">Preencha os campos e salve.</DrawerDescription>
          </DrawerHeader>
          <div className="max-h-[75vh] overflow-y-auto px-4 pb-6">{children}</div>
        </DrawerContent>
      </Drawer>
    );
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription className="sr-only">Preencha os campos e salve.</DialogDescription>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}

function todayIso(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function toInput(n: number): string {
  return n.toFixed(2).replace(".", ",");
}

const NEW_CATEGORY = "__new__";

function EntryForm({ target, onDone }: { target: NonNullable<Target>; onDone: () => void }) {
  const qc = useQueryClient();
  const isExpense = target.kind === "expense";
  const item = target.item;

  const [amount, setAmount] = useState(item ? toInput(item.amount) : "");
  const [date, setDate] = useState(item?.occurred_on ?? todayIso());
  const [description, setDescription] = useState(item?.description ?? "");
  const [categoryId, setCategoryId] = useState<string>(
    isExpense && item ? String((item as Expense).category.id) : "",
  );
  const [newCatOpen, setNewCatOpen] = useState(false);
  const [newCatName, setNewCatName] = useState("");
  const [newCatError, setNewCatError] = useState<string | null>(null);

  const [amountError, setAmountError] = useState<string | null>(null);
  const [dateError, setDateError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [monthClosed, setMonthClosed] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving, setSaving] = useState(false);

  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: api.getCategories,
    enabled: isExpense,
  });

  // Default to the category flagged is_default ("Outros") on new expenses.
  useEffect(() => {
    if (isExpense && !item && !categoryId && categories.data) {
      const def = categories.data.find((c) => c.is_default);
      if (def) setCategoryId(String(def.id));
    }
  }, [categories.data, isExpense, item, categoryId]);

  const visibleCategories = (categories.data ?? []).filter(
    (c) => c.is_active || String(c.id) === categoryId,
  );

  async function refresh() {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["expenses"] }),
      qc.invalidateQueries({ queryKey: ["extra_incomes"] }),
      qc.invalidateQueries({ queryKey: ["home"] }),
    ]);
  }

  function handleError(e: unknown) {
    if (e instanceof ApiError && e.code === "future_date") setDateError(e.message);
    else if (e instanceof ApiError && e.code === "month_closed") setMonthClosed(e.message);
    else setFormError(errorMessage(e));
  }

  async function save(dateOverride?: string) {
    setAmountError(null);
    setDateError(null);
    setFormError(null);
    const value = parseMoneyInput(amount);
    if (Number.isNaN(value)) {
      setAmountError("Digite um valor, por exemplo 25,90.");
      return;
    }
    const body: Record<string, unknown> = {
      amount: value,
      occurred_on: dateOverride ?? date,
      description: description.trim() || null,
    };
    if (isExpense && categoryId) body["category_id"] = Number(categoryId);
    setSaving(true);
    try {
      if (isExpense) {
        if (item) await api.updateExpense(item.id, body);
        else await api.createExpense(body);
      } else {
        if (item) await api.updateExtraIncome(item.id, body);
        else await api.createExtraIncome(body);
      }
      await refresh();
      onDone();
    } catch (e) {
      handleError(e);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!item) return;
    setSaving(true);
    setFormError(null);
    try {
      if (isExpense) await api.deleteExpense(item.id);
      else await api.deleteExtraIncome(item.id);
      await refresh();
      onDone();
    } catch (e) {
      setFormError(errorMessage(e));
    } finally {
      setSaving(false);
      setConfirmDelete(false);
    }
  }

  async function createCategory() {
    setNewCatError(null);
    if (!newCatName.trim()) {
      setNewCatError("Digite o nome da categoria.");
      return;
    }
    try {
      const created = (await api.createCategory({ name: newCatName.trim() })) as { id: number };
      await qc.invalidateQueries({ queryKey: ["categories"] });
      setCategoryId(String(created.id));
      setNewCatOpen(false);
      setNewCatName("");
    } catch (e) {
      setNewCatError(errorMessage(e));
    }
  }

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <div className="grid gap-2">
        <Label htmlFor="entry-amount">Valor</Label>
        <Input
          id="entry-amount"
          autoFocus
          inputMode="decimal"
          placeholder="0,00"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="h-11 tabular-nums"
          aria-invalid={!!amountError}
        />
        {amountError && <p className="text-sm text-destructive">{amountError}</p>}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="entry-date">Data</Label>
        <Input
          id="entry-date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="h-11"
          aria-invalid={!!dateError}
        />
        {dateError && <p className="text-sm text-destructive">{dateError}</p>}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="entry-description">Descrição (opcional)</Label>
        <Input
          id="entry-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="h-11"
        />
      </div>

      {isExpense && (
        <div className="grid gap-2">
          <Label htmlFor="entry-category">Categoria (opcional)</Label>
          <Select
            value={categoryId}
            onValueChange={(v) => {
              if (v === NEW_CATEGORY) setNewCatOpen(true);
              else setCategoryId(v);
            }}
          >
            <SelectTrigger id="entry-category" className="h-11">
              <SelectValue placeholder="Escolha uma categoria" />
            </SelectTrigger>
            <SelectContent>
              {visibleCategories.map((c) => (
                <SelectItem key={c.id} value={String(c.id)} className="min-h-11">
                  {c.name}
                </SelectItem>
              ))}
              <SelectItem value={NEW_CATEGORY} className="min-h-11 text-primary">
                Criar nova categoria
              </SelectItem>
            </SelectContent>
          </Select>
          {newCatOpen && (
            <div className="grid gap-2 rounded-lg border border-border p-3">
              <Label htmlFor="new-category">Nome da nova categoria</Label>
              <Input
                id="new-category"
                autoFocus
                value={newCatName}
                onChange={(e) => setNewCatName(e.target.value)}
                className="h-11"
              />
              {newCatError && <p className="text-sm text-destructive">{newCatError}</p>}
              <div className="flex gap-2">
                <Button type="button" className="h-11 flex-1" onClick={createCategory}>
                  Criar
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="h-11 flex-1"
                  onClick={() => setNewCatOpen(false)}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {formError && (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm"
        >
          {formError}
        </p>
      )}

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
        {item ? (
          <Button
            type="button"
            variant="outline"
            className="h-11 text-destructive"
            disabled={saving}
            onClick={() => setConfirmDelete(true)}
          >
            Apagar
          </Button>
        ) : (
          <span />
        )}
        <Button type="submit" className="h-11" disabled={saving}>
          {saving ? "Salvando…" : "Salvar"}
        </Button>
      </div>

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

      <AlertDialog open={monthClosed !== null} onOpenChange={(o) => !o && setMonthClosed(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Mês fechado</AlertDialogTitle>
            <AlertDialogDescription>{monthClosed}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="h-11">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="h-11"
              onClick={() => {
                const t = todayIso();
                setDate(t);
                setMonthClosed(null);
                void save(t);
              }}
            >
              Usar a data de hoje
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </form>
  );
}
