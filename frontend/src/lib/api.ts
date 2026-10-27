import type {
  CategoryItem,
  CreditCard,
  Expense,
  ExtraIncome,
  FixedExpense,
  Home,
  MonthDetail,
  MonthItem,
  SavingsQuota,
  Settings,
} from "@/lib/types";

// Endereço da API. Para outro endereço, defina VITE_API_URL.
export const API_URL: string = import.meta.env["VITE_API_URL"] ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  code: string;
  params: Record<string, unknown>;
  constructor(status: number, code: string, message: string, params: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.params = params;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      ...(body !== undefined
        ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
        : {}),
    });
  } catch {
    throw new ApiError(0, "network", "network");
  }
  const text = await res.text();
  let json: { code?: string; message?: string; params?: Record<string, unknown> } | null = null;
  if (text) {
    try {
      json = JSON.parse(text);
    } catch {
      // Corpo que não é JSON (por exemplo, uma página de erro de um proxy).
      throw new ApiError(res.status, "internal_error", "");
    }
  }
  if (!res.ok) {
    throw new ApiError(
      res.status,
      json?.code ?? "internal_error",
      json?.message ?? "",
      json?.params ?? {},
    );
  }
  return json as T;
}

type Body = Record<string, unknown>;

export const api = {
  getHome: () => request<Home>("GET", "/home"),
  getSettings: () => request<Settings>("GET", "/settings"),
  saveSettings: (current_salary: number) =>
    request<unknown>("PUT", "/settings", { current_salary }),
  updateMonthSalary: (salary: number) =>
    request<unknown>("PATCH", "/months/current/salary", { salary }),
  dismissNotice: (id: number) => request<unknown>("POST", `/notices/${id}/dismiss`),

  getMonths: () => request<MonthItem[]>("GET", "/months"),
  getMonth: (id: number) => request<MonthDetail>("GET", `/months/${id}`),
  decideLeftover: (monthId: number, decision: "carried" | "declined") =>
    request<unknown>("POST", `/months/${monthId}/leftover-decision`, { decision }),

  getExpenses: () => request<Expense[]>("GET", "/expenses"),
  createExpense: (body: Body) => request<unknown>("POST", "/expenses", body),
  updateExpense: (id: number, body: Body) => request<unknown>("PATCH", `/expenses/${id}`, body),
  deleteExpense: (id: number) => request<unknown>("DELETE", `/expenses/${id}`),

  getExtraIncomes: () => request<ExtraIncome[]>("GET", "/extra-incomes"),
  createExtraIncome: (body: Body) => request<unknown>("POST", "/extra-incomes", body),
  updateExtraIncome: (id: number, body: Body) =>
    request<unknown>("PATCH", `/extra-incomes/${id}`, body),
  deleteExtraIncome: (id: number) => request<unknown>("DELETE", `/extra-incomes/${id}`),

  getCategories: () => request<CategoryItem[]>("GET", "/categories"),
  createCategory: (body: Body) => request<unknown>("POST", "/categories", body),
  updateCategory: (id: number, body: Body) => request<unknown>("PATCH", `/categories/${id}`, body),

  getFixedExpenses: () => request<FixedExpense[]>("GET", "/fixed-expenses"),
  createFixedExpense: (body: Body) => request<unknown>("POST", "/fixed-expenses", body),
  updateFixedExpense: (id: number, body: Body) =>
    request<unknown>("PATCH", `/fixed-expenses/${id}`, body),

  getSavingsQuotas: () => request<SavingsQuota[]>("GET", "/savings-quotas"),
  createSavingsQuota: (body: Body) => request<unknown>("POST", "/savings-quotas", body),
  updateSavingsQuota: (id: number, body: Body) =>
    request<unknown>("PATCH", `/savings-quotas/${id}`, body),

  getCreditCards: () => request<CreditCard[]>("GET", "/credit-cards"),
  createCreditCard: (body: Body) => request<unknown>("POST", "/credit-cards", body),
  updateCreditCard: (id: number, body: Body) =>
    request<unknown>("PATCH", `/credit-cards/${id}`, body),
  updateReportedValue: (id: number, reportedValue: number, type?: "payment" | "refund") =>
    request<unknown>("PUT", `/credit-cards/${id}/current-month`, {
      reported_value: reportedValue,
      ...(type ? { type } : {}),
    }),
  registerPayment: (id: number, amount: number) =>
    request<unknown>("POST", `/credit-cards/${id}/current-month/payments`, { amount }),
  updateCardEntry: (id: number, body: Body) =>
    request<unknown>("PATCH", `/credit-card-entries/${id}`, body),
  deleteCardEntry: (id: number) => request<unknown>("DELETE", `/credit-card-entries/${id}`),
};
