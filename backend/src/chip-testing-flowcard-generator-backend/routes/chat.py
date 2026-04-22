from fastapi import APIRouter

from schema.fastapi_request.chat import ChatRequest, UpdateChatRequest
import component.chat
import util

router = APIRouter(prefix='/chats', tags=['chats'])


@router.get('')
async def get_chats() -> list[dict[str, str]]:
    """获取所有聊天的ID和标题"""
    return component.chat.get_all_chats()


@router.get('/{chat_id}')
async def get_chat(chat_id: str) -> list[dict[str, str]]:
    """获取单个聊天的全部对话历史"""
    history = await component.chat.load_history(chat_id)
    return component.chat.convert_messages_to_dicts(history)


@router.delete('/{chat_id}')
async def delete_chat(chat_id: str) -> bool:
    """删除指定的聊天"""
    return await component.chat.delete_chat(chat_id)


@router.post('')
async def create_chat() -> str:
    """开启一个新聊天，返回chat_id"""
    return util.generate_unique_id(unique_checking_sequence=[_chat['id'] for _chat in component.chat.get_all_chats()])


@router.post('/{chat_id}/chat')
async def chat(chat_id:str, request: ChatRequest):
    """
    与大语言模型交流。
    chat_id: 聊天ID。
    message: 用户发出的单条消息。
    using_docs: 要使用的知识库文档ID的列表，用于RAG检索。如果为空，则不使用RAG。
    k: RAG在每个文档中查找k条语义最相关的内容。
    reranking_k: RAG在每个文档中查找reranking_k条语义最相关的内容，重排序后取k条结果。如果为None，则不使用重排序（加快响应速度）。
    :return: 大语言模型响应。
    """
    return await component.chat.chat(
        request.message,
        request.using_docs,
        request.k,
        request.reranking_k,
        chat_id
    )


@router.put('/{chat_id}')
async def update_chat_title(chat_id: str, request: UpdateChatRequest):
    """修改聊天的标题"""
    return await component.chat.update_chat_title(chat_id, request.new_title)
