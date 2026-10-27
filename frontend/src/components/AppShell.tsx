import { useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  CreditCard,
  History,
  Home,
  Plus,
  Receipt,
  Settings,
  Wallet,
  TrendingUp,
} from "lucide-react";
import { EntryFormsProvider, useEntryForms } from "@/components/EntryForms";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const NAV = [
  { to: "/", label: "Início", icon: Home },
  { to: "/transactions", label: "Lançamentos", icon: Receipt },
  { to: "/credit-cards", label: "Cartão", icon: CreditCard },
  { to: "/history", label: "Histórico", icon: History },
  { to: "/registry", label: "Cadastros", icon: Settings },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <EntryFormsProvider>
      <Shell>{children}</Shell>
    </EntryFormsProvider>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const { openExpense, openIncome } = useEntryForms();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [chooserOpen, setChooserOpen] = useState(false);

  if (pathname === "/setup") return <>{children}</>;

  const isActive = (to: string) => (to === "/" ? pathname === "/" : pathname.startsWith(to));

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar (wide) */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-border bg-card px-4 py-8 md:flex">
        <div className="mb-10 flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Wallet className="h-5 w-5" aria-hidden />
          </div>
          <span className="text-sm font-semibold leading-5">
            Financial
            <br />
            Assistant
          </span>
        </div>
        <nav className="flex flex-col gap-1" aria-label="Navegação principal">
          {NAV.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              aria-current={isActive(to) ? "page" : undefined}
              className={`flex min-h-12 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors ${
                isActive(to)
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
            >
              <Icon className="h-5 w-5" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      <div className="md:pl-60">
        {/* Desktop top bar */}
        <div className="mx-auto hidden max-w-3xl justify-end px-8 pt-8 md:flex">
          <Button className="h-11 gap-2" onClick={() => openExpense()}>
            <Plus className="h-4 w-4" aria-hidden />
            Novo gasto
          </Button>
        </div>
        <main className="mx-auto max-w-3xl px-5 pb-32 pt-8 md:px-8 md:pb-12">{children}</main>
      </div>

      {/* FAB (mobile) */}
      <Button
        type="button"
        size="icon"
        aria-label="Novo lançamento"
        onClick={() => setChooserOpen(true)}
        className="fixed bottom-20 right-5 z-40 h-14 w-14 rounded-full shadow-soft md:hidden"
      >
        <Plus className="h-6 w-6" aria-hidden />
      </Button>

      {/* Bottom tabs (mobile) */}
      <nav
        aria-label="Navegação principal"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-card pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            aria-current={isActive(to) ? "page" : undefined}
            className={`flex min-h-16 flex-col items-center justify-center gap-1 border-t-2 text-[11px] font-medium ${
              isActive(to)
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground"
            }`}
          >
            <Icon className="h-5 w-5" aria-hidden />
            {label}
          </Link>
        ))}
      </nav>

      {/* Chooser */}
      <Dialog open={chooserOpen} onOpenChange={setChooserOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>O que você quer lançar?</DialogTitle>
            <DialogDescription>Escolha o tipo de lançamento.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Button
              variant="outline"
              className="h-12 justify-start gap-3"
              onClick={() => {
                setChooserOpen(false);
                openExpense();
              }}
            >
              <Receipt className="h-5 w-5" aria-hidden /> Novo gasto
            </Button>
            <Button
              variant="outline"
              className="h-12 justify-start gap-3"
              onClick={() => {
                setChooserOpen(false);
                openIncome();
              }}
            >
              <TrendingUp className="h-5 w-5" aria-hidden /> Nova renda extra
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
