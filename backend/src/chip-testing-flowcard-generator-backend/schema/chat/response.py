from pydantic import BaseModel, Field

from schema.knowledge import SemanticSearchHit


class ChatResponse(BaseModel):
    answer: str = Field(description='模型回答内容')
    rag_hits: list[SemanticSearchHit] = Field(description='本次请求命中的RAG结果', default_factory=list)
