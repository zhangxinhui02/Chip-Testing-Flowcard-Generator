import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Literal, Callable, Sequence, List

from config import common_config
from schema.task_manager import Task
from util.generate_unique_id import generate_unique_id

common_processing_list: List[Task] = []
gpu_processing_list: List[Task] = []

common_pending_list: List[Task] = []
gpu_pending_list: List[Task] = []


def __get_all_task_ids() -> List[str]:
    task_ids = []
    task_ids.extend([task.task_id for task in common_processing_list])
    task_ids.extend([task.task_id for task in gpu_processing_list])
    task_ids.extend([task.task_id for task in common_pending_list])
    task_ids.extend([task.task_id for task in gpu_pending_list])
    return task_ids


async def run_task(
        task_type: Literal['COMMON', 'GPU'],
        fn: Callable,
        args: Sequence = (),
        object_id: str | None = None
):
    """此协程函数向任务管理器注册一个阻塞型的后台任务，当队列有空闲时在进程池中运行，运行完毕后返回Task对象"""
    global common_processing_list, gpu_processing_list, common_pending_list, gpu_pending_list

    # 构建Task对象，用于管理任务状态
    _task = Task(
        task_id=generate_unique_id(unique_checking_sequence=__get_all_task_ids()),
        task_type=task_type,
        object_id=object_id,
        status='PENDING',
        fn=fn,
        args=args
    )

    # 根据不同任务类型获取不同参数
    if _task.task_type == 'COMMON':
        _processing_list = common_processing_list
        _pending_list = common_pending_list
        _parallel_processing_count = common_config.common_task_parallel_processing_count
    else:
        _processing_list = gpu_processing_list
        _pending_list = gpu_pending_list
        _parallel_processing_count = common_config.gpu_task_parallel_processing_count

    # 如果运行队列空闲就设置为运行状态，否则加入等待队列
    if len(_processing_list) < _parallel_processing_count:
        _task.status = 'RUNNING'
        _processing_list.append(_task)
    else:
        _pending_list.append(_task)

    # 如果处于等待状态，则循环检查，间隔0.1秒：若运行队列空闲且本任务为等待队列第一个任务，则跳出循环并开始运行
    if _task.status == 'PENDING':
        while True:
            await asyncio.sleep(0.1)
            if (len(_processing_list) < _parallel_processing_count) and (_pending_list[0] is _task):
                break
        _pending_list.pop(0)
        _task.status = 'RUNNING'
        _processing_list.append(_task)

    # 在进程池中运行任务
    with ProcessPoolExecutor(max_workers=_parallel_processing_count) as executor:
        loop = asyncio.get_event_loop()
        try:
            _task.return_result = await loop.run_in_executor(
                executor,
                _task.fn,
                *_task.args
            )
            _task.status = 'SUCCESS'
        except Exception as e:
            _task.status = 'FAILURE'
            _task.exception = e
        _processing_list.remove(_task)
        return _task
