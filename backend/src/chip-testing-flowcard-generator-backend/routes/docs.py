import os
import asyncio
import logging
import aiofiles
from typing import Literal
from fastapi import APIRouter, UploadFile, File

from config import const_config
from component import knowledge
from schema.knowledge import Doc
from util import generate_unique_id

logger = logging.getLogger(__name__)
temp_file_path = os.path.join(const_config.temp_dir, 'route-docs')
os.makedirs(temp_file_path, exist_ok=True)
router = APIRouter(prefix='/docs', tags=['docs'])


@router.get('/', response_model=list[Doc])
async def get_docs() -> list[Doc]:
    """获取所有的文档信息"""
    return await knowledge.get_all_docs()


@router.put('/{doc_id}', response_model=bool)
async def update_doc(doc_id: str, new_title: str, new_note: str) -> bool:
    """修改文档的标题和备注"""
    try:
        return await knowledge.update_doc_info(doc_id, new_title, new_note)
    except Exception as e:
        logger.error(e)
        return False


@router.post('/', response_model=bool)
async def create_doc(
        title: str,
        file_type: Literal['image', 'pdf', 'markdown', 'txt'],
        note: str,
        file: UploadFile = File(...)
) -> bool:
    """创建文档。此任务耗时较长，会直接返回响应，后端会继续处理"""
    _file_path = os.path.join(temp_file_path, file.filename if file.filename else generate_unique_id())
    async with aiofiles.open(_file_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):  # 1MB
            await f.write(chunk)

    def _clean(_: asyncio.Task):
        """清理下载的文件"""
        if os.path.isfile(_file_path):
            os.remove(_file_path)

    task = asyncio.create_task(  # 此任务耗时较长，直接返回响应，后台继续处理
        knowledge.vectorize_doc_to_db(
            title,
            _file_path,
            file_type,
            note,
            False
        )
    )
    task.add_done_callback(_clean)  # 清理临时文件
    return True


@router.delete('/{doc_id}')
async def delete_doc(doc_id: str):
    """删除文档"""
    return await knowledge.delete_doc(doc_id)
