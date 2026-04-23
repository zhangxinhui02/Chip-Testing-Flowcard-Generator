import os
import asyncio
import logging
import aiofiles
from typing import Literal
from fastapi.responses import FileResponse
from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from schema.fastapi_request.knowledge import UpdateDocRequest, CreateDocRequest
from schema.knowledge import Doc
from config import const_config
from component import knowledge
from util import generate_unique_id

logger = logging.getLogger(__name__)
temp_file_dir = os.path.join(const_config.temp_dir, 'route-docs')
storage_dir = os.path.join(const_config.storage_dir, 'knowledge')
os.makedirs(temp_file_dir, exist_ok=True)
router = APIRouter(prefix='/docs', tags=['docs'])


@router.get('')
async def get_docs() -> list[Doc]:
    """获取所有的文档信息"""
    return await knowledge.get_all_docs()


@router.put('/{doc_id}')
async def update_doc(doc_id: str, request: UpdateDocRequest) -> bool:
    """修改文档的标题和备注"""
    try:
        return await knowledge.update_doc_info(doc_id, request.new_title, request.new_note)
    except Exception as e:
        logger.error(e)
        return False


@router.post('')
async def create_doc(
        title: str = Form(...),
        file_type: Literal['image', 'pdf', 'markdown', 'txt'] = Form(...),
        note: str = Form(''),
        file: UploadFile = File(...)
) -> bool:
    """创建文档。此任务耗时较长，会直接返回响应，后端会继续处理"""
    request = CreateDocRequest(title=title, file_type=file_type, note=note)
    _file_path = os.path.join(temp_file_dir, file.filename if file.filename else generate_unique_id())
    async with aiofiles.open(_file_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):  # 1MB
            await f.write(chunk)

    def _clean(_: asyncio.Task):
        """清理下载的文件"""
        if os.path.isfile(_file_path):
            os.remove(_file_path)

    task = asyncio.create_task(  # 此任务耗时较长，直接返回响应，后台继续处理
        knowledge.vectorize_doc_to_db(
            request.title,
            _file_path,
            request.file_type,
            request.note,
            False
        )
    )
    task.add_done_callback(_clean)  # 清理临时文件
    return True


@router.delete('/{doc_id}')
async def delete_doc(doc_id: str):
    """删除文档"""
    return await knowledge.delete_doc(doc_id)


@router.get('/{doc_id}/file')
async def get_doc_file(doc_id: str) -> FileResponse:
    """下载文档的原始文件"""
    if doc_id in knowledge.built_in_docs_map:
        _target_dir = os.path.join(const_config.built_in_docs_dir, knowledge.built_in_docs_map[doc_id])
        _target_files = [_file for _file in os.listdir(_target_dir) if _file.startswith(f'target.')]

        if len(_target_files) > 0:
            if len(_target_files) > 1:
                _target_files.remove('target.md')
            file_path = os.path.join(_target_dir, _target_files[0])
            return FileResponse(
                path=file_path,
                filename=f'{knowledge.built_in_docs_map[doc_id]}.{_target_files[0].split(".")[-1]}'
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")

    file_name = None
    for _file_name in os.listdir(storage_dir):
        if _file_name.startswith(f'{doc_id}-'):
            file_name = _file_name
            break

    if file_name is None:
        raise HTTPException(status_code=404, detail="File not found")
    else:
        file_path = os.path.join(storage_dir, file_name)
        original_file_name = file_name.lstrip(f'{doc_id}-')
        return FileResponse(
            path=file_path,
            filename=original_file_name
        )
