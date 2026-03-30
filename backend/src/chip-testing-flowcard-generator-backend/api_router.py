import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from config import common_config

logger = logging.getLogger(__file__)

@asynccontextmanager
async def lifespan(_):
    pass
    yield
    pass

app = FastAPI(lifespan=lifespan)


@app.get("/api")
def root():
    return {"message": "Hello World"}


def run():
    """运行uvicorn服务器，阻塞当前线程"""
    uvicorn.run(
        app,
        host=common_config.listen_host,
        port=common_config.listen_port
    )
