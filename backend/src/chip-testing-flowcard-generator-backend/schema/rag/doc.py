from typing import Literal
from pydantic import BaseModel

class Doc(BaseModel):
    title: str
    id: str
    status: Literal['ok', 'creating', 'failed']
    note: str = ''
