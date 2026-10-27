const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function formatMoney(value: number): string {
  return brl.format(value);
}

/** "2026-10-17" -> "17/10/2026" */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

const MONTHS = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

export function formatMonthYear(year: number, monthNumber: number): string {
  return `${MONTHS[monthNumber - 1]} de ${year}`;
}

export function daysLeftLabel(daysLeft: number): string {
  if (daysLeft === 0) return "Último dia do mês";
  if (daysLeft === 1) return "Falta 1 dia";
  return `Faltam ${daysLeft} dias`;
}

/** Accepts "1.234,56" or "1234,56" or "1234.56". Returns NaN if invalid. */
export function parseMoneyInput(input: string): number {
  const s = input.trim().replace(/\s|R\$/g, "");
  if (!s) return NaN;
  const normalized = s.includes(",") ? s.replace(/\./g, "").replace(",", ".") : s;
  return /^\d+(\.\d{1,2})?$/.test(normalized) ? Number(normalized) : NaN;
}
