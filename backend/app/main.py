"""Monta o app: cria o FastAPI, liga CORS e hosts permitidos, registra as rotas.

So liga as pecas. Para rodar, dentro de backend/:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.dependencies import run_month_routine
from app.api.error_handlers import register_error_handlers
from app.api.routers import (
    categories,
    credit_cards,
    expenses,
    extra_incomes,
    fixed_expenses,
    home,
    months,
    savings_quotas,
    settings,
)
from app.config import load_config
from app.controllers.setup_controller import ensure_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_database()  # cria o arquivo do banco se ele ainda nao existe
    yield


def create_app() -> FastAPI:
    config = load_config()
    # A rotina do mes roda antes de toda rota (e quase sempre nao faz nada).
    app = FastAPI(
        title="Financial Assistant",
        lifespan=lifespan,
        dependencies=[Depends(run_month_routine)],
    )
    app.state.allowed_origins = config.allowed_origins

    # Hosts: contra DNS rebinding, so aceita 127.0.0.1 e localhost (ALLOWED_HOSTS).
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.allowed_hosts))
    # CORS por ultimo, para ficar por fora e cobrir tambem as respostas de erro.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    for module in (
        home,
        months,
        settings,
        fixed_expenses,
        savings_quotas,
        categories,
        expenses,
        extra_incomes,
        credit_cards,
    ):
        app.include_router(module.router)
    return app


app = create_app()
