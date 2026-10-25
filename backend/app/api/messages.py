MONTH_NAMES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

_RESOURCE_NAMES = {
    "fixed_expense": "o gasto fixo",
    "savings_quota": "a cota",
    "category": "a categoria",
    "expense": "o gasto",
    "extra_income": "a renda extra",
    "credit_card": "o cartão",
    "credit_card_entry": "a linha do cartão",
    "month": "o mês",
}

def brl(value: float) -> str:
    text = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {text}" if value < 0 else f"R$ {text}"

def month_name(label: str) -> str:
    return MONTH_NAMES[int(label.split("-")[1]) - 1]

def join_pt(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " e " + items[-1]

def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]

def error_message(code: str, params: dict) -> str:
    if code == "value_decreased":
        return (
            f"O valor do cartão diminuiu {brl(params['difference'])}. "
            "Foi um pagamento ou um estorno?"
        )
    if code == "month_closed":
        return (
            f"O mês de {month_name(params['closed_month'])} já fechou. "
            f"Quer registrar em {month_name(params['current_month'])}?"
        )
    if code == "future_date":
        return "Não é possível registrar com data de mês futuro. Escolha uma data deste mês."
    if code == "payment_exceeds_reported_value":
        return (
            f"O pagamento de {brl(params['amount'])} é maior que o valor informado "
            f"do cartão ({brl(params['reported_value'])})."
        )
    if code == "leftover_income_locked":
        return "Esta renda veio da sobra do mês e não pode ser editada nem apagada."
    if code == "leftover_not_pending":
        return "Esta sobra já foi respondida ou o mês não teve sobra."
    if code == "no_open_month":
        return "Informe o seu salário em Cadastros antes de fazer lançamentos."
    if code == "name_already_exists":
        return f"Já existe uma categoria chamada \"{params['name']}\"."
    if code == "default_category_locked":
        return "A categoria \"Outros\" não pode ser desativada."
    if code == "category_inactive":
        return "Esta categoria está desativada. Escolha outra."
    if code == "validation_error":
        fields = [item["field"] for item in params.get("fields", [])]
        return f"Dados inválidos. Confira: {join_pt(fields)}." if fields else "Dados inválidos."
    if code == "not_found":
        if params.get("resource") == "credit_card_month":
            return "Este cartão não tem total neste mês. Reative o cartão para criar o total."
        name = _RESOURCE_NAMES.get(params.get("resource", ""), "o item pedido")
        return f"Não encontramos {name}."
    if code == "method_not_allowed":
        return "Esta rota não aceita esse método."
    if code == "internal_error":
        return "Algo deu errado no servidor. Tente de novo em instantes."
    return "Não foi possível concluir a operação."

def notice_message(code: str, params: dict) -> str:
    if code == "month_ending":
        days_left = params["days_left"]
        cards = params.get("has_active_cards", False)
        if days_left == 0:
            text = "Hoje é o último dia do mês."
            return text + (" Atualize o valor dos cartões antes de virar." if cards else "")
        text = "O mês fecha em 1 dia." if days_left == 1 else f"O mês fecha em {days_left} dias."
        return text + (" Atualize o valor dos cartões." if cards else "")

    if code == "credit_card_not_updated":
        names = params["card_names"]
        if len(names) == 1:
            return f"O cartão {names[0]} ainda não foi atualizado neste mês."
        return f"Os cartões {join_pt(names)} ainda não foram atualizados neste mês."

    if code == "month_closed_negative":
        closed = _capitalize(month_name(params["closed_month"]))
        current = month_name(params["current_month"])
        return (
            f"{closed} fechou no negativo ({brl(abs(params['final_balance']))} abaixo de zero). "
            f"O valor não passa para {current}."
        )

    if code == "unused_months":
        names = [month_name(label) for label in params["months"]]
        if len(names) == 1:
            return f"O mês de {names[0]} ficou sem registro, porque o app não foi aberto."
        return f"Os meses de {join_pt(names)} ficaram sem registro, porque o app não foi aberto."

    return "Há um aviso para você."


def leftover_message(month_number: int, amount: float) -> str:
    name = _capitalize(MONTH_NAMES[month_number - 1])
    return f"{name} fechou com sobra de {brl(amount)}. Quer levar esse valor para este mês?"
