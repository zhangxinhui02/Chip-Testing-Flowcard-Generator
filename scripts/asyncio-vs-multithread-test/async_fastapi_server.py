import asyncio
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Async FastAPI Benchmark Server")


@app.get("/io", response_class=PlainTextResponse)
async def io_task(delay: float = 0.5):
    await asyncio.sleep(delay)
    return "ok"


@app.get("/health")
async def health():
    return {"status": "ok"}
