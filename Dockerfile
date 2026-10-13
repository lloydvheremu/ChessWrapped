# ---- Stage 1: builder -------------------------------------------------------
FROM python:3.12-slim AS builder

# gcc brings binutils, which provides `strip` for the step below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    # Compiled extensions ship with debug symbols; stripping them cuts ~38MB.
    && find /install -name "*.so" -exec strip --strip-unneeded {} +

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /install /usr/local

WORKDIR /app
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
