# Job Application Tracker API

FastAPI + PostgreSQL REST API with JWT auth, per-user data isolation, status-change history and SQL analytics.

## Run
    docker compose up --build        # API at http://localhost:8000/docs
    # or locally with SQLite:
    pip install -r requirements.txt && uvicorn app.main:app --reload

## Test
    pytest -q

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | /auth/register, /auth/login | get a JWT |
| POST/GET | /applications | create, list (filter `status`, search `q`, paginate) |
| GET/PATCH/DELETE | /applications/{id} | read, update (status changes are logged), delete |
| GET | /analytics/summary | counts by status, response rate, follow-ups due |

## Design notes
- `status_events` stores every status change, enabling time-in-stage analytics later.
- Every query is scoped to the authenticated user; other users get 404.
- Roadmap: React frontend, Alembic migrations, deploy to Render.
