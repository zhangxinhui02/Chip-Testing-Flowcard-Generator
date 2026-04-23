from pydantic import BaseModel

class CreateFlowcardRequest(BaseModel):
    title: str | None = None
    order_doc_id: str | None = None
    order_message: str | None = None
    chip_code: str | None = None
    using_doc_ids: list[str] = []
    k: int = 10
    reranking_k: int | None = None

class UpdateFlowcardTitleRequest(BaseModel):
    new_title: str
