"""Excecoes do app. Sem logica: so o codigo e os dados de cada erro.

Todas as camadas podem importar este arquivo. O core levanta o erro, e a api
o transforma em resposta HTTP (status, `message` em portugues e `params`)
sem as duas camadas se conhecerem.
"""


class AppError(Exception):
    """Base dos erros de regra de negocio. `code` e `params` vao para a resposta da API."""

    code = "app_error"

    def __init__(self, **params: object) -> None:
        super().__init__(self.code)
        self.params = params


class MonthClosedError(AppError):
    """Lancamento com data de um mes que ja fechou."""

    code = "month_closed"

    def __init__(self, closed_month: str, current_month: str) -> None:
        super().__init__(closed_month=closed_month, current_month=current_month)


class FutureDateError(AppError):
    """Lancamento com data de mes futuro."""

    code = "future_date"


class ValueDecreasedError(AppError):
    """Valor do cartao menor que o anterior, sem dizer se foi pagamento ou estorno."""

    code = "value_decreased"

    def __init__(self, difference: float) -> None:
        super().__init__(difference=difference)


class PaymentExceedsReportedValueError(AppError):
    """Pagamento maior que o valor informado do cartao."""

    code = "payment_exceeds_reported_value"

    def __init__(self, amount: float, reported_value: float) -> None:
        super().__init__(amount=amount, reported_value=reported_value)


class LeftoverIncomeLockedError(AppError):
    """Tentativa de editar ou apagar a renda extra que veio da sobra."""

    code = "leftover_income_locked"


class LeftoverNotPendingError(AppError):
    """Decisao da sobra para um mes sem sobra pendente (nao teve sobra ou ja foi decidida)."""

    code = "leftover_not_pending"

    def __init__(self, decision: str | None) -> None:
        super().__init__(decision=decision)


class NotFoundError(AppError):
    """O registro pedido nao existe. A API responde 404."""

    code = "not_found"

    def __init__(self, resource: str, resource_id: int) -> None:
        super().__init__(resource=resource, id=resource_id)


class NoOpenMonthError(AppError):
    """Operacao que precisa de um mes aberto, mas o salario ainda nao foi informado."""

    code = "no_open_month"


class NameAlreadyExistsError(AppError):
    """Ja existe uma categoria com este nome (sem diferenciar maiuscula de minuscula)."""

    code = "name_already_exists"

    def __init__(self, name: str) -> None:
        super().__init__(name=name)


class DefaultCategoryLockedError(AppError):
    """A categoria padrao "Outros" nao pode ser desativada."""

    code = "default_category_locked"


class CategoryInactiveError(AppError):
    """Categoria desativada nao pode ser escolhida para um gasto novo ou alterado."""

    code = "category_inactive"

    def __init__(self, category_id: int) -> None:
        super().__init__(category_id=category_id)
