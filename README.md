# Wagah System

FastAPI web application for managing traveler processing at the Wagah border crossing: master records (ITS-based traveler data), transport fleets (bus, train, plane), seat bookings, and an admin dashboard with user management.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env
```

Required in `.env`:

- `SECRET_KEY` - generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `INITIAL_ADMIN_PASSWORD` - used once, on first startup with an empty users table, to create the initial admin account (`INITIAL_ADMIN_USERNAME`, default `admin`). Without it no account is created and you cannot log in.

`DATABASE_URL` defaults to `sqlite:///./wagah.db`. Set `COOKIE_SECURE=False` for plain-HTTP local development.

## Run

```bash
alembic upgrade head    # create/upgrade the schema
python main.py          # http://localhost:8000
```

Or `./run_all.sh`, which runs the migration, the periodic backup job (`backup.py`), and the app.

## Tests

```bash
pytest
```

## Layout

- `main.py` - app wiring: middleware (auth state, CSRF, security headers, rate limiting), error pages, startup admin bootstrap
- `routers/` - auth, admin, master, transport, booking
- `middleware/`, `config/` - auth/CSRF middleware, settings, security helpers
- `database.py` - SQLAlchemy models; schema managed by Alembic (`alembic/`)
- `templates/`, `static/` - Jinja2 templates (Tailwind) and assets
- `backup.py` - hourly SQLite snapshot via the online backup API; restore by copying `backups/wagah_backup.db` over the database file while the app is stopped

## Legacy

`custom.py`, `arrived.py`, `sim.py`, `bus.py`, `train.py`, `plane.py`, `admin.py`, `modify.py`, `delete.py` are standalone apps that predate `main.py`. They bypass its security stack and are not started by `run_all.sh`. They remain only because some features (master creation, arrival tracking, SIM assignment, ITS printing, bulk deletes) have not been migrated to `routers/` yet. Do not expose them publicly.
