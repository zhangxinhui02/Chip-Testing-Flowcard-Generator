from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    using_docs: list[str]
    k: int = 10
    reranking_k: int | None = None

class UpdateChatRequest(BaseModel):
    new_title: str
