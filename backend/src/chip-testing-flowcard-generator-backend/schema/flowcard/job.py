from pydantic import BaseModel, Field

class Job(BaseModel):
    name: str = Field(description="工序，即工序名称")
    requirement: str = Field(description="条件要求")
    start_and_end_time: str = Field(description="作业起止时间", default='')
    result: str = Field(description="作业结果")
    operator: str = Field(description="作业员")
    note: str = Field(description="备注", default='')
