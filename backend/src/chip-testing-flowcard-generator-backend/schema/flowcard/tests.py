from pydantic import BaseModel, Field

class Test(BaseModel):
    name: str = Field(description="筛选项")

class Tests(BaseModel):
    chip_code: str = Field(description="芯片型号")
    tests: list[Test] = Field(description="若干个筛选项")
    note: str = Field(description="备注文本")
