from pydantic import BaseModel, Field
from .job import Job

class Flowcard(BaseModel):
    jobs: list[Job] = Field(description="存储此流程卡的所有工序的列表", default=[])
