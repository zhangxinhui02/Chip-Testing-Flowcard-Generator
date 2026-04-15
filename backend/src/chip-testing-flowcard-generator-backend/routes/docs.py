from typing import Literal
from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix='/docs', tags=['docs'])


@router.get('/')
def get_docs():
    """获取所有的文档信息"""
    pass


@router.get('/{doc_id}')
def get_doc(doc_id: str):
    """获取指定ID的文档的详细信息"""
    pass


@router.post('/')
def create_doc(
        title: str,
        file_type: Literal['image', 'pdf', 'markdown', 'txt'],
        file: UploadFile = File(...)
) -> str:
    """创建文档"""
    pass


@router.delete('/{doc_id}')
def delete_doc(doc_id: str):
    """删除文档"""
    pass
