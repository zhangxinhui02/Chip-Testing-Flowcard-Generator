from fastapi import APIRouter

from schema.fastapi_request.flowcards import CreateFlowcardRequest
from schema.flowcard import Flowcard
from component import flowcard

router = APIRouter(prefix='/flowcards', tags=['flowcards'])


@router.get('')
async def get_flowcards() -> dict[str, Flowcard]:
    """获取所有历史生成的流程卡"""
    return await flowcard.get_flowcards()


@router.delete('/{flowcard_id}')
async def get_flowcards(flowcard_id: str) -> bool:
    """删除流程卡"""
    return await flowcard.delete_flowcard(flowcard_id)


@router.post('')
async def create_flowcard(request: CreateFlowcardRequest) -> tuple[str, Flowcard]:
    """
    生成新流程卡，返回ID和流程卡对象
    必须至少提供order_doc_id或者order_message中的一者,order_doc_id优先
    如果未提供order_doc_id而提供了order_message，那么必须提供chip_code
    using_doc_ids内的文档ID对应的文档会参与到RAG检索中，留空则不进行RAG检索
    k: RAG在每个文档中查找k条语义最相关的内容
    reranking_k: RAG在每个文档中查找reranking_k条语义最相关的内容，重排序后取k条结果。如果为None，则不使用重排序（加快响应速度）
    """
    return await flowcard.geneate_flowcard(
        request.order_doc_id,
        request.order_message,
        request.chip_code,
        request.using_doc_ids,
        request.k,
        request.reranking_k
    )
