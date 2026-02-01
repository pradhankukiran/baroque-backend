# Baroque Backend

FastAPI + Rococo backend for the Claude API Usage Leaderboard.

## Prerequisites

- Python 3.10+
- PostgreSQL 14+

## Setup (Local)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run migrations
psql -d baroque -f migrations/postgres/001_initial_schema.sql
psql -d baroque -f migrations/postgres/002_add_model_column.sql

# Run server
python run.py
```

## Setup (Docker)

```bash
# Development
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml up -d
```

## Environment Variables

```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=secret
DATABASE_NAME=baroque

ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-...
FRONTEND_URL=http://localhost:9000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/models` | List available models |
| POST | `/api/register` | Register developer |
| GET | `/api/leaderboard` | Get rankings |
| GET | `/api/developer/{id}/stats` | Personal stats |

## Scheduler

The app fetches usage data from Anthropic Admin API every 5 minutes automatically.
