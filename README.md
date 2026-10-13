# Chess Wrapped

A personal chess stats API. Give it a Lichess username — get back a
Spotify Wrapped-style breakdown of that player's recent games.

## Demo

<!-- Record a short terminal session: curl the /wrapped endpoint, show the JSON response. Use any screen-to-GIF tool.
     Save it as docs/demo.gif, then move the line below out of this comment:
![Demo](docs/demo.gif)
-->

_Demo recording coming soon. Until then, the [example response](#endpoints) below shows what you get back._

## What it demonstrates

- Designing a versioned REST API with typed request/response contracts
- Integrating an external API that returns non-standard response formats (NDJSON)
- Caching expensive API calls with PostgreSQL and TTL-based invalidation
- Containerising a multi-service Python app with Docker Compose
- Separating infrastructure concerns (migrations, health checks, startup ordering)
- Mapping upstream failures to clear HTTP errors (404 for unknown players, 502 when Lichess fails, 504 on timeouts)

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Daily driver, comfort zone |
| Framework | FastAPI | Async-native, auto Swagger docs |
| HTTP client | httpx | Async-first, clean API |
| Validation | Pydantic v2 | Typed request/response contracts |
| Database | PostgreSQL 16 | Caching game history |
| ORM | SQLAlchemy 2 (async) | Industry standard |
| Container | Docker + Docker Compose | Portfolio DevOps requirement |
| Migrations | Alembic | Schema version control |

## Architecture

```
┌──────────────────────────────────────┐
│           Docker Compose             │
│                                      │
│  ┌─────────────┐  ┌───────────────┐  │
│  │  FastAPI    │  │  PostgreSQL   │  │
│  │  :8000      │──│  cache layer  │  │
│  └──────┬──────┘  └───────────────┘  │
│         │                            │
└─────────┼────────────────────────────┘
          │ HTTPS
    Lichess public API
    (lichess.org/api)
```

On startup, Compose waits for Postgres to pass its health check, runs a one-off
`migrate` container (`alembic upgrade head`), and only then starts the API.
`/wrapped` results are stored in Postgres for an hour (`CACHE_TTL_SECONDS`), so
repeat requests skip Lichess entirely. The design decisions are explained in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/player/{username}` | Basic profile: ratings, country, join date |
| GET | `/api/v1/wrapped/{username}` | Full Wrapped stats object for the last 50 games (cached for 1 hour) |
| GET | `/api/v1/openings/{username}` | Top 5 openings by games played, each with its win rate |
| GET | `/health` | Liveness check — always returns 200 |

Interactive docs for every endpoint are at `http://localhost:8000/docs`.

**Player profile**

```bash
curl http://localhost:8000/api/v1/player/DrNykterstein
```

**Wrapped stats**

```bash
curl http://localhost:8000/api/v1/wrapped/DrNykterstein
```

Example response:

```json
{
  "username": "knightking",
  "period": "last_50_games",
  "total_games": 50,
  "win_rate": 0.54,
  "draw_rate": 0.08,
  "loss_rate": 0.38,
  "best_streak": 7,
  "favourite_time_control": "blitz",
  "favourite_opening": {
    "eco": "B20",
    "name": "Sicilian Defence",
    "games_played": 34,
    "win_rate": 0.61
  },
  "best_accuracy_game": {
    "game_id": "abc123",
    "accuracy": 94.2,
    "opponent": "someuser",
    "result": "win",
    "url": "https://lichess.org/abc123"
  },
  "cached_at": "2026-09-13T10:00:00Z"
}
```

`cached_at` is `null` on a fresh fetch and holds the time the result was stored
when it is served from the cache. `favourite_opening` and `best_accuracy_game`
are `null` when none of the games have opening or computer-analysis data.

**Top openings**

```bash
curl http://localhost:8000/api/v1/openings/DrNykterstein
```

**Health check**

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**Errors**

| Situation | Status | Body |
|---|---|---|
| Username not on Lichess (or account closed) | 404 | `{"detail": "Player not found on Lichess"}` |
| Lichess returns an error or is unreachable | 502 | `{"detail": "Lichess API error"}` |
| Lichess takes longer than 30 seconds | 504 | `{"detail": "Lichess request timed out"}` |

## How to run

### With Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

Then: `open http://localhost:8000/docs`

### Without Docker (local dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL to your local Postgres instance in .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Running tests

```
Tests are not included in this version. Integration tests using pytest-asyncio
and httpx test client are planned for a future iteration.
```

## Project context

I built Chess Wrapped as one step in a portfolio progression that goes from
Python and FastAPI, through Docker, to Kubernetes. This project covers the first
two stages: a typed async API that talks to a real third-party service, and a
multi-container setup that starts from a clean machine with one command. The next
project in the arc takes this same service and deploys it to Kubernetes with a
GitHub Actions CI/CD pipeline.
