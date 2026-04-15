import logging
import uvicorn
from typing import Literal
from fastapi import FastAPI, UploadFile, File
from contextlib import asynccontextmanager

from config import const_config, common_config

logger = logging.getLogger(__file__)
prefix = const_config.api_prefix

@asynccontextmanager
async def lifespan(_):
    pass
    yield
    pass

app = FastAPI(lifespan=lifespan)


@app.get(f"{prefix}/")
def root():
    return {"message": "Hello World"}


# 知识库
@app.get(f'{prefix}/docs')
def get_docs():
    """获取所有的文档信息"""
    pass

@app.post(f'{prefix}/docs')
def create_doc(title: str, file_type: Literal['image', 'pdf', 'markdown', 'txt'], file: UploadFile = File(...)):
    """创建文档"""


def run():
    """运行uvicorn服务器，阻塞当前线程"""
    uvicorn.run(
        app,
        host=common_config.listen_host,
        port=common_config.listen_port
    )
