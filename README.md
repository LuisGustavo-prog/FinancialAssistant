# Financial Assistant

A personal monthly spending tracker for a single user, running entirely on your own computer.
The back end is a Python API (FastAPI) backed by SQLite. The front end is a React app that talks only to the API.

The month's free balance is calculated as: salary + extra income - fixed expenses - savings quotas - debit expenses - credit card totals.

## Structure

```
backend/    Python API (core with the rules, db, controllers, api)
frontend/   React front end (talks only to the API)
docker-compose.yml
```

The API only accepts connections from your own computer (`127.0.0.1`). The database file lives in `backend/data/` and is never committed to Git.

## Run without Docker

Back end (port 8000), inside `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The database is created automatically on the first start. The interactive API documentation is at `http://127.0.0.1:8000/docs`.

Front end (port 8080), inside `frontend/` and with the API running (requires Node 20.19+ or 22.12+):

```bash
npm ci
npm run dev
```

Open `http://127.0.0.1:8080`.

## Run with Docker

From the project root:

```bash
docker compose up --build
```

The API is available at `http://127.0.0.1:8000` and the front end at `http://127.0.0.1:8080`. The database stays in the `backend/data/` folder on your computer, even after `docker compose down`.

## Tests and code style

Inside `backend/`, with the virtual environment active:

```bash
pytest              # run all tests
ruff check .        # lint the code
ruff format .       # format the code
```

With Docker: `docker compose run --rm api pytest`.

## Database backup

Inside `backend/`, with the virtual environment active. The command uses SQLite's safe backup API and can run while the API is up:

```bash
mkdir -p ~/backups
python -c "import sqlite3, sys; o = sqlite3.connect('data/financial_assistant.db'); b = sqlite3.connect(sys.argv[1]); o.backup(b)" ~/backups/financial_assistant-$(date +%F).db
```

To restore, stop the API and copy the file back to `backend/data/financial_assistant.db`.
