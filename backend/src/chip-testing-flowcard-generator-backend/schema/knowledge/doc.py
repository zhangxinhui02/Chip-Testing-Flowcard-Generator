from typing import Literal
from pydantic import BaseModel

class Doc(BaseModel):
    title: str  # 文档标题
    id: str  # 文档唯一ID
    status: Literal['ok', 'creating', 'failed']  # 文档状态
    note: str = ''  # 文档备注
    is_built_in: bool = False  # 是否为内建文档
