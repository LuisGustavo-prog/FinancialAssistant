-- Financial_Assistant: schema do banco (versao 1).
-- Fonte da verdade da estrutura. O Python nao cria nem altera tabelas.
--
-- Convencoes:
--   * Dinheiro: REAL com no maximo 2 casas (CHECK amount = ROUND(amount, 2)).
--   * Datas: TEXT 'AAAA-MM-DD' (CHECK date(x) IS x recusa formato e dia invalido).
--   * Booleanos: INTEGER 0 ou 1.
--   * Nenhuma tabela usa ON DELETE CASCADE: meses, cartoes e categorias nunca
--     sao apagados. Unica excecao: template_id vira NULL se o modelo sumir.
--   * Em CHECK, NULL passa. Por isso colunas obrigatorias tem NOT NULL e as
--     datas usam "IS" (date(NULL) IS NULL e verdadeiro, data invalida nao).

-- ---------------------------------------------------------------------------
-- Configuracao (uma linha so). Sem salario ainda = current_salary NULL.
-- ---------------------------------------------------------------------------
CREATE TABLE settings (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    current_salary    REAL
        CHECK (current_salary >= 0 AND current_salary = ROUND(current_salary, 2)),
    last_checked_date TEXT
        CHECK (date(last_checked_date) IS last_checked_date),
    pending_notices   TEXT NOT NULL DEFAULT '[]'
        CHECK (CASE WHEN json_valid(pending_notices)
                    THEN json_type(pending_notices) = 'array'
                    ELSE 0 END)
);

-- ---------------------------------------------------------------------------
-- Mes. Aberto: sem resultado. Fechado: resultado, saldo final e data.
-- ---------------------------------------------------------------------------
CREATE TABLE month (
    id                INTEGER PRIMARY KEY,
    year              INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    month_number      INTEGER NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    status            TEXT    NOT NULL CHECK (status IN ('open', 'closed')),
    salary            REAL    NOT NULL
        CHECK (salary >= 0 AND salary = ROUND(salary, 2)),
    result            TEXT CHECK (result IN ('green', 'red')),
    final_balance     REAL CHECK (final_balance = ROUND(final_balance, 2)),
    closed_at         TEXT CHECK (date(closed_at) IS closed_at),
    leftover_decision TEXT
        CHECK (leftover_decision IN ('pending', 'carried', 'declined')),
    UNIQUE (year, month_number),
    CONSTRAINT month_state_fields CHECK (
        (status = 'open'
            AND result IS NULL AND final_balance IS NULL
            AND closed_at IS NULL AND leftover_decision IS NULL)
        OR
        (status = 'closed'
            AND result IS NOT NULL AND final_balance IS NOT NULL
            AND closed_at IS NOT NULL)
    ),
    CONSTRAINT month_result_matches_balance CHECK (
        status = 'open'
        OR result = CASE WHEN final_balance >= 0 THEN 'green' ELSE 'red' END
    ),
    CONSTRAINT month_decision_only_with_leftover CHECK (
        status = 'open'
        OR ((final_balance > 0) = (leftover_decision IS NOT NULL))
    )
);

-- No maximo um mes aberto por vez.
CREATE UNIQUE INDEX one_open_month ON month (status) WHERE status = 'open';

-- ---------------------------------------------------------------------------
-- Modelos (valem do mes atual em diante) e copias por mes.
-- ---------------------------------------------------------------------------
CREATE TABLE fixed_expense_template (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL CHECK (length(trim(name)) > 0),
    amount    REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE savings_quota_template (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL CHECK (length(trim(name)) > 0),
    amount    REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE month_fixed_expense (
    id          INTEGER PRIMARY KEY,
    month_id    INTEGER NOT NULL REFERENCES month (id),
    template_id INTEGER REFERENCES fixed_expense_template (id) ON DELETE SET NULL,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    amount      REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    UNIQUE (month_id, template_id)
);
CREATE INDEX idx_month_fixed_expense_month ON month_fixed_expense (month_id);

CREATE TABLE month_savings_quota (
    id          INTEGER PRIMARY KEY,
    month_id    INTEGER NOT NULL REFERENCES month (id),
    template_id INTEGER REFERENCES savings_quota_template (id) ON DELETE SET NULL,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    amount      REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    UNIQUE (month_id, template_id)
);
CREATE INDEX idx_month_savings_quota_month ON month_savings_quota (month_id);

-- ---------------------------------------------------------------------------
-- Renda extra. source 'leftover' e a sobra que o sistema lanca sozinho.
-- ---------------------------------------------------------------------------
CREATE TABLE extra_income (
    id          INTEGER PRIMARY KEY,
    month_id    INTEGER NOT NULL REFERENCES month (id),
    amount      REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    occurred_on TEXT NOT NULL CHECK (date(occurred_on) IS occurred_on),
    description TEXT,
    source      TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'leftover'))
);
CREATE INDEX idx_extra_income_month ON extra_income (month_id, occurred_on);

-- ---------------------------------------------------------------------------
-- Categorias e gastos (debito).
-- ---------------------------------------------------------------------------
CREATE TABLE category (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(name)) > 0),
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    CONSTRAINT category_default_stays_active CHECK (is_default = 0 OR is_active = 1)
);
CREATE UNIQUE INDEX one_default_category ON category (is_default) WHERE is_default = 1;

CREATE TABLE expense (
    id             INTEGER PRIMARY KEY,
    month_id       INTEGER NOT NULL REFERENCES month (id),
    amount         REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    occurred_on    TEXT NOT NULL CHECK (date(occurred_on) IS occurred_on),
    description    TEXT,
    category_id    INTEGER NOT NULL REFERENCES category (id),
    payment_method TEXT NOT NULL DEFAULT 'debit' CHECK (payment_method IN ('debit'))
);
CREATE INDEX idx_expense_month ON expense (month_id, occurred_on);
CREATE INDEX idx_expense_category ON expense (category_id);

-- ---------------------------------------------------------------------------
-- Cartao de credito: valor informado do mes + pagamentos e estornos.
-- ---------------------------------------------------------------------------
CREATE TABLE credit_card (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL CHECK (length(trim(name)) > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE credit_card_month (
    id             INTEGER PRIMARY KEY,
    credit_card_id INTEGER NOT NULL REFERENCES credit_card (id),
    month_id       INTEGER NOT NULL REFERENCES month (id),
    reported_value REAL NOT NULL DEFAULT 0
        CHECK (reported_value >= 0 AND reported_value = ROUND(reported_value, 2)),
    updated_at     TEXT CHECK (date(updated_at) IS updated_at),
    UNIQUE (credit_card_id, month_id)
);
CREATE INDEX idx_credit_card_month_month ON credit_card_month (month_id);

CREATE TABLE credit_card_entry (
    id                   INTEGER PRIMARY KEY,
    credit_card_month_id INTEGER NOT NULL REFERENCES credit_card_month (id),
    type                 TEXT NOT NULL CHECK (type IN ('payment', 'refund')),
    amount               REAL NOT NULL CHECK (amount > 0 AND amount = ROUND(amount, 2)),
    occurred_on          TEXT NOT NULL CHECK (date(occurred_on) IS occurred_on)
);
CREATE INDEX idx_credit_card_entry_month ON credit_card_entry (credit_card_month_id, occurred_on);

-- ---------------------------------------------------------------------------
-- Dados iniciais: a linha unica de configuracao e a categoria padrao.
-- ---------------------------------------------------------------------------
INSERT INTO settings (id) VALUES (1);
INSERT INTO category (name, is_default, is_active) VALUES ('Outros', 1, 1);

PRAGMA user_version = 1;
