from typing import Literal
from pydantic import BaseModel

class UpdateDocRequest(BaseModel):
    new_title: str
    new_note: str

class CreateDocRequest(BaseModel):
    title: str
    file_type: Literal['image', 'pdf', 'markdown', 'txt']
    note: str
