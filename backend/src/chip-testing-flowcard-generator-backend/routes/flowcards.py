from typing import Literal
from fastapi import APIRouter

router = APIRouter(prefix='/flowcards', tags=['flowcards'])


@router.get('/')
def get_flowcards():
    """获取所有历史生成的流程卡"""
    pass


@router.get('/{flowcard_id}')
def get_flowcard(flowcard_id: str):
    """获取指定流程卡的详细信息"""
    pass


@router.post('/')
def create_flowcard(
        title: str,
        order_type: Literal['text', 'image', 'pdf'],
        using_docs: list[str]
) -> str:
    """生成流程卡"""
    pass
