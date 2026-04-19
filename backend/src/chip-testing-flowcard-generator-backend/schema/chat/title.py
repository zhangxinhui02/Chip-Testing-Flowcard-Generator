from pydantic import BaseModel, Field

class ChatTitle(BaseModel):
    title: str = Field(description='对话的标题')
