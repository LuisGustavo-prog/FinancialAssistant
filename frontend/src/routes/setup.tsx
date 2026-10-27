import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { parseMoneyInput } from "@/lib/format";
import { errorMessage } from "@/components/StateViews";

export const Route = createFileRoute("/setup")({
  head: () => ({
    meta: [
      { name: "description", content: "Informe seu salário mensal para começar." },
      { property: "og:description", content: "Informe seu salário mensal para começar." },
    ],
  }),
  component: SetupPage,
});

function SetupPage() {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const salary = parseMoneyInput(value);
    if (Number.isNaN(salary)) {
      setError("Digite um valor, por exemplo 4500,00.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.saveSettings(salary);
      qc.removeQueries({ queryKey: ["home"] });
      navigate({ to: "/" });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-soft"
      >
        <Wallet className="h-8 w-8 text-primary" aria-hidden />
        <h1 className="mt-4 text-2xl font-semibold">Bem-vindo</h1>
        <p className="mt-1 text-muted-foreground">Vamos configurar seu controle de gastos.</p>
        <div className="mt-6 grid gap-2">
          <Label htmlFor="salary">Qual é o seu salário mensal?</Label>
          <Input
            id="salary"
            inputMode="decimal"
            placeholder="0,00"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="h-11 tabular-nums"
            aria-invalid={!!error}
            aria-describedby={error ? "salary-error" : undefined}
          />
          {error && (
            <p id="salary-error" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>
        <Button type="submit" className="mt-6 h-11 w-full" disabled={saving}>
          {saving ? "Salvando…" : "Começar"}
        </Button>
      </form>
    </div>
  );
}
