export type Category = { id: number; name: string };
export type Expense = {
  id: number;
  amount: number;
  occurred_on: string;
  description: string | null;
  category: Category;
  payment_method: string;
};
export type ExtraIncome = {
  id: number;
  amount: number;
  occurred_on: string;
  description: string | null;
  source: string;
  is_editable?: boolean;
};
export type Notice = {
  id: number | null;
  code:
    "month_ending" | "credit_card_not_updated" | "month_closed_negative" | "unused_months" | string;
  params: Record<string, unknown>;
  message: string;
};
export type Breakdown = {
  salary: number;
  extra_incomes: number;
  fixed_expenses: number;
  savings_quotas: number;
  debit_expenses: number;
  credit_card_total: number;
};
export type PendingLeftover = {
  month_id: number;
  year: number;
  month_number: number;
  amount: number;
  message: string;
};
export type HomeOk = {
  status: "ok";
  month: { id: number; year: number; month_number: number; status: string; days_left: number };
  free_balance: number;
  breakdown: Breakdown;
  notices: Notice[];
  pending_leftover: PendingLeftover | null;
  recent_expenses: Expense[];
};
export type Home = HomeOk | { status: "needs_setup" };

export type CategoryItem = { id: number; name: string; is_default: boolean; is_active: boolean };

export type CardEntry = {
  id: number;
  type: "payment" | "refund" | string;
  amount: number;
  occurred_on: string;
};
export type CreditCard = {
  id: number;
  name: string;
  is_active: boolean;
  in_current_month: boolean;
  reported_value: number | null;
  payments_total: number | null;
  total: number | null;
  updated_at: string | null;
  days_since_update: number | null;
  is_outdated: boolean;
  entries: CardEntry[];
};

export type Settings = { current_salary: number; current_month_salary: number };

export type FixedExpense = { id: number; name: string; amount: number; is_active: boolean };
export type SavingsQuota = { id: number; name: string; amount: number; is_active: boolean };

export type MonthItem = {
  id: number;
  year: number;
  month_number: number;
  status: string;
  result: string;
  final_balance: number;
  leftover_decision: "pending" | "carried" | "declined" | null;
};

export type MonthDetail = MonthItem & {
  breakdown: Breakdown;
  expenses: Expense[];
  extra_incomes: ExtraIncome[];
  fixed_expenses: { name: string; amount: number }[];
  savings_quotas: { name: string; amount: number }[];
  credit_cards: { id: number; name: string; total: number }[];
};
