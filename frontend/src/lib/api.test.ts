import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, API_URL } from "@/lib/api";

function stubFetch(response: Response | Error) {
  const fn = vi.fn(async () => {
    if (response instanceof Error) throw response;
    return response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("chama a rota certa com o método certo", async () => {
    const fetchMock = stubFetch(new Response(JSON.stringify({ status: "needs_setup" })));

    const home = await api.getHome();

    expect(home).toEqual({ status: "needs_setup" });
    expect(fetchMock).toHaveBeenCalledWith(`${API_URL}/home`, { method: "GET" });
  });

  it("envia o corpo em JSON e aceita resposta vazia (204)", async () => {
    const fetchMock = stubFetch(new Response(null, { status: 204 }));

    await api.dismissNotice(7);
    await api.registerPayment(1, 50);

    expect(fetchMock).toHaveBeenNthCalledWith(1, `${API_URL}/notices/7/dismiss`, {
      method: "POST",
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `${API_URL}/credit-cards/1/current-month/payments`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: 50 }),
      },
    );
  });

  it("transforma o erro da API em ApiError, com code, message e params", async () => {
    stubFetch(
      new Response(
        JSON.stringify({
          code: "payment_exceeds_reported_value",
          message: "O pagamento é maior que o valor informado.",
          params: { amount: 900 },
        }),
        { status: 422 },
      ),
    );

    const error = await api.registerPayment(1, 900).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: "payment_exceeds_reported_value",
      message: "O pagamento é maior que o valor informado.",
      params: { amount: 900 },
    });
  });

  it("usa o código network quando a API não responde", async () => {
    stubFetch(new TypeError("Failed to fetch"));

    const error = await api.getHome().catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("network");
  });

  it("não quebra quando o corpo do erro não é JSON", async () => {
    stubFetch(new Response("<html>Bad Gateway</html>", { status: 502 }));

    const error = await api.getHome().catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 502, code: "internal_error" });
  });
});
