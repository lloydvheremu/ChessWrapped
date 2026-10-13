# Architecture decisions

This document explains the main design choices behind Chess Wrapped, for readers
who want more depth than the README gives.

## Why FastAPI over Flask or Django

The service spends almost all of its time waiting on Lichess, so an async-native
framework is the natural fit: while one request waits on the network, the same
worker can serve others. FastAPI is built on ASGI and async from the ground up,
whereas Flask's async support sits on top of a synchronous core and Django brings
an ORM, admin and templating layer this API does not need. FastAPI also turns the
Pydantic response models into OpenAPI documentation automatically, so the
Swagger UI at `/docs` always matches the real response shapes, and responses are
validated against those models before they leave the service.

## Why PostgreSQL as a cache instead of Redis

Redis would be the textbook choice for a pure key-value cache, but here it would
mean running and operating a second datastore for one table. The cached value is
a single computed `WrappedStats` document per player, read far more often than it
is written, which Postgres handles comfortably as one indexed row stored as JSON.
Expiry is done in the application: each row records `cached_at`, and a read that
finds a row older than `CACHE_TTL_SECONDS` deletes it and fetches fresh data.
Postgres also gives durability Redis does not by default, so the cache survives
`docker compose down` and restarts, and Alembic keeps the schema under version
control. If traffic ever outgrew this, the cache sits behind two functions in
`app/services/cache.py` (`get_cached` and `set_cached`) and could be swapped for
Redis without touching the routers.

## Why NDJSON parsing matters and how it is handled

Lichess's game export endpoint does not return a JSON array. It streams
newline-delimited JSON (NDJSON): one complete JSON object per line, so clients
can process games as they arrive. Calling `response.json()` on that body fails,
because the body as a whole is not valid JSON. The client requests it explicitly
with `Accept: application/x-ndjson`, splits the body on newlines, skips blank
lines (including the trailing newline), and decodes each line with
`json.loads()`, giving the aggregator a plain list of game dicts. The request is
capped at 200 games and bounded by a 30-second timeout, and the aggregator
tolerates missing optional fields such as `opening` or `analysis`, anonymous
opponents, and unfinished or aborted games, which Lichess reports without a
winner just as it does for draws.

## Why the multi-stage Docker build

Several dependencies (asyncpg, uvloop, SQLAlchemy's extensions) include compiled
code, and the build stage carries the tools for that: `gcc`, `libpq-dev` and
binutils. None of them are needed to run the app, so the builder installs the
Python packages into a separate `/install` prefix, strips debug symbols from the
compiled extensions, and the runtime stage starts again from a clean
`python:3.12-slim` and copies in only that prefix plus the application code. The
result is a smaller image with no compilers in it, which means less to download
and less attack surface. The runtime container also runs as a non-root
`appuser`, and the Compose health check uses the Python standard library rather
than installing curl, so the runtime stage needs no extra system packages at all.
