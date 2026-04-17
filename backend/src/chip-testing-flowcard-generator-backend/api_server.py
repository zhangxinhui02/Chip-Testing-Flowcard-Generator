import logging
import uvicorn
from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager

from config import const_config, common_config
import routes
import component.knowledge

logger = logging.getLogger(__file__)
prefix = const_config.api_prefix


@asynccontextmanager
async def lifespan(_):
    """FastAPI生命周期管理器"""
    await component.rag.init_milvus_database()
    yield
    pass


app = FastAPI(lifespan=lifespan)
api_prefixed = APIRouter(prefix=prefix)
api_prefixed.include_router(routes.docs_router)
api_prefixed.include_router(routes.flowcard_router)
api_prefixed.include_router(routes.qa_router)
app.include_router(api_prefixed)


def run():
    """运行uvicorn服务器，阻塞当前线程"""
    uvicorn.run(
        app,
        host=common_config.listen_host,
        port=common_config.listen_port
    )
