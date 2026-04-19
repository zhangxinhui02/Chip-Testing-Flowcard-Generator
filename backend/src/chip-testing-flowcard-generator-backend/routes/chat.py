from fastapi import APIRouter

router = APIRouter(prefix='/qa', tags=['qa'])


@router.get('/chats')
def get_chats():
    """获取所有聊天列表"""
    pass


@router.get('/chats/{chat_id}')
def get_chat(chat_id: str):
    """获取单个聊天的全部对话历史"""
    pass


@router.delete('/chats/{chat_id}')
def delete_chat(chat_id: str):
    """删除指定的聊天"""
    pass


@router.post('/chats')
def create_chat() -> str:
    """开启新聊天"""
    pass


@router.post('/chats/{chat_id}/chat')
def chat(chat_id: str, using_docs: list[str]):
    """在指定聊天中发送信息并接收响应"""
    pass
