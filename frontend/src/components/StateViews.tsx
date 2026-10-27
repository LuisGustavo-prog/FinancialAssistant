import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

const SERVER_ERROR = "Não consegui falar com o servidor. Confira se o app está rodando.";

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code !== "network" && error.message) return error.message;
  return SERVER_ERROR;
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-border bg-card p-6 text-center shadow-soft"
    >
      <p className="text-sm font-medium text-destructive">Erro</p>
      <p className="mt-1 text-foreground">{errorMessage(error)}</p>
      <Button className="mt-4 h-11" onClick={onRetry}>
        Tentar de novo
      </Button>
    </div>
  );
}

export function EmptyState({ text, action }: { text: string; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-border p-6 text-center">
      <p className="text-muted-foreground">{text}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-2xl font-semibold tracking-tight">{children}</h1>;
}
