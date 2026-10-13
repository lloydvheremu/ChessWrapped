from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.routers import stats  # noqa: E402  (env must be loaded first)

app = FastAPI(title="Chess Wrapped API", version="0.1.0")
app.include_router(stats.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
