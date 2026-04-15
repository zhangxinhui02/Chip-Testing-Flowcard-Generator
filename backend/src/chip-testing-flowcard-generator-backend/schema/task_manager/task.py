from pydantic import BaseModel, ConfigDict
from typing import Literal, Callable, Sequence

class Task(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    task_id: str
    task_type: Literal['COMMON', 'GPU']
    object_id: str | None = None
    status: Literal['PENDING', 'RUNNING', 'SUCCESS', 'FAILURE'] = 'PENDING'
    fn: Callable
    args: Sequence = ()
    return_result: object = None
    exception: Exception = None
