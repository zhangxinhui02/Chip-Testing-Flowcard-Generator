import os
import json
import aiofiles
from typing import Sequence
from pydantic import SecretStr
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from config import const_config, llm_model_config
from util import generate_unique_id
from schema.chat import ChatTitle
from component import knowledge

chat_storage_dir = os.path.join(const_config.storage_dir, 'chat')
prompts_dir = const_config.prompts_dir

llm_client = ChatOpenAI(
    api_key=SecretStr(llm_model_config.api_key),
    base_url=llm_model_config.base_url,
    model=llm_model_config.model,
    temperature=0.7
)
generate_title_parser = PydanticOutputParser(pydantic_object=ChatTitle)

__is_initialized = False
cached_chat_history = {}
chat_history_timeout = {}
prompts = {}

if not __is_initialized:
    with open(os.path.join(chat_storage_dir, 'metadata.json'), 'r', encoding='utf-8') as _f:
        cached_chat_metadata: dict = json.load(_f)
    for _title in ['common-pre-prompt', 'chat-with-docs', 'chat', 'generate-chat-title']:
        with open(os.path.join(prompts_dir, f'{_title}.md'), 'r', encoding='utf-8') as _f:
            prompts[_title]: str= _f.read()
    __is_initialized = True


async def __add_chat_metadata(chat_id: str, title: str):
    """保存chat_id的title到单独的文件中，方便查找"""
    if cached_chat_metadata.get(chat_id, None) is None:
        cached_chat_metadata[chat_id] = {}
    cached_chat_metadata[chat_id]['title'] = title
    async with aiofiles.open(os.path.join(chat_storage_dir, 'chats.json'), 'w', encoding='utf-8') as f:
        await f.write(json.dumps(cached_chat_metadata, ensure_ascii=False, indent=4))


async def __delete_chat_metadata(chat_id: str):
    """删除指定chat_id的元信息"""
    if chat_id in cached_chat_metadata:
        del cached_chat_metadata[chat_id]
        async with aiofiles.open(os.path.join(chat_storage_dir, 'chats.json'), 'w', encoding='utf-8') as f:
            await f.write(json.dumps(cached_chat_metadata, ensure_ascii=False, indent=4))


async def __update_chat_metadata(chat_id: str, title: str):
    """修改指定chat_id的元信息"""
    if chat_id in cached_chat_metadata:
        cached_chat_metadata['title'] = title
        async with aiofiles.open(os.path.join(chat_storage_dir, 'chats.json'), 'w', encoding='utf-8') as f:
            await f.write(json.dumps(cached_chat_metadata, ensure_ascii=False, indent=4))


def convert_messages_to_dicts(messages: list[BaseMessage]) -> list[dict]:
    """将BaseMessage对象列表转换为dict列表"""
    results = []
    for message in messages:
        if isinstance(message, SystemMessage):
            results.append({
                'type': 'SystemMessage',
                'content': message.content
            })
        elif isinstance(message, HumanMessage):
            results.append({
                'type': 'HumanMessage',
                'content': message.content
            })
        else:  # AIMessage
            results.append({
                'type': 'AIMessage',
                'content': message.content
            })
    return results


def convert_dicts_to_messages(dicts: list[dict]) -> list[BaseMessage]:
    """将dict列表转换为BaseMessage对象列表"""
    results = []
    for message in dicts:
        if message['type'] == 'SystemMessage':
            results.append(SystemMessage(message['content']))
        elif message['type'] == 'HumanMessage':
            results.append(HumanMessage(message['content']))
        else:  # AIMessage
            results.append(AIMessage(message['content']))
    return results


async def __dump_persistent_history(chat_id: str, history: list[BaseMessage]):
    """将聊天历史保存到持久化存储"""
    _history = convert_messages_to_dicts(history)
    content = json.dumps(_history, ensure_ascii=False, indent=4)
    async with aiofiles.open(os.path.join(chat_storage_dir, f'{chat_id}.json'), 'w', encoding='utf-8') as f:
        await f.write(content)


async def __load_persistent_history(chat_id: str) -> list[BaseMessage]:
    """从持久化存储中读取聊天历史"""
    if not os.path.isfile(os.path.join(chat_storage_dir, f'{chat_id}.json')):
        return []
    async with aiofiles.open(os.path.join(chat_storage_dir, f'{chat_id}.json'), 'r', encoding='utf-8') as f:
        content = await f.read()
    json_history = json.loads(content)
    history = convert_dicts_to_messages(json_history)
    return history


async def __delete_timeout_chat_history_cache():
    """移除超时的聊天历史缓存"""
    now = datetime.now()
    for chat_id, delete_time in chat_history_timeout.items():
        if delete_time >= now:
            del cached_chat_history[chat_id]


async def dump_history(chat_id: str, history: list[BaseMessage]):
    """保存聊天历史到缓存和持久化存储"""
    cached_chat_history[chat_id] = history
    await __dump_persistent_history(chat_id, history)
    chat_history_timeout[chat_id] = datetime.now() + timedelta(minutes=const_config.chat_histoy_cache_minutes)
    await __delete_timeout_chat_history_cache()


async def load_history(chat_id: str) -> list[BaseMessage]:
    """读取聊天历史，优先读缓存，缓存不存在时从持久化存储中读取"""
    if cached_chat_history.get(chat_id, None) is None:
        cached_chat_history[chat_id] = await __load_persistent_history(chat_id)
    chat_history_timeout[chat_id] = datetime.now() + timedelta(minutes=const_config.chat_histoy_cache_minutes)
    await __delete_timeout_chat_history_cache()
    return cached_chat_history[chat_id]


async def __generate_chat_title(message: str) -> str:
    """根据传入的消息为聊天生成一个标题"""
    prompt = PromptTemplate(
        template=prompts['generate-chat-title'],
        input_variables=['MESSAGE'],
        partial_variables={'FORMAT': generate_title_parser.get_format_instructions()}
    )
    chain = prompt | llm_client | generate_title_parser
    chat_title: ChatTitle = await chain.ainvoke({'MESSAGE': message})
    return chat_title.title


def get_all_chats() -> list[dict[str, str]]:
    """获取所有聊天的id和标题"""
    return [
        {
            'id': _chat_id,
            'title': cached_chat_metadata[_chat_id]['title']
        }
        for _chat_id in cached_chat_metadata
    ]


async def delete_chat(chat_id: str) -> bool:
    """从缓存和持久化存储中删除聊天"""
    await __delete_chat_metadata(chat_id)
    del cached_chat_history[chat_id]
    del chat_history_timeout[chat_id]
    os.remove(os.path.join(chat_storage_dir, f'{chat_id}.json'))
    return True


async def update_chat_title(chat_id: str, title: str) -> bool:
    """更新聊天的标题"""
    await __update_chat_metadata(chat_id, title)
    return True


async def chat(
    message: str,
    using_doc_ids: Sequence[str] = (),
    k: int = 10,
    reranking_k: int | None = None,
    chat_id: str | None = None
) -> str:
    """与大语言模型交流，可选多个文档用于RAG"""
    if chat_id is None:  # 新聊天
        chat_id: str = generate_unique_id(unique_checking_sequence=list(cached_chat_metadata.keys()))
        title = await __generate_chat_title(message)
        await __add_chat_metadata(chat_id, title)
        history: list[BaseMessage] = [SystemMessage(prompts['common-pre-prompt'])]
    else:
        history: list[BaseMessage] = await load_history(chat_id)

    if len(using_doc_ids) > 0:
        results = await knowledge.query_from_docs(message, using_doc_ids, k=k, reranking_k=reranking_k)
        _docs_prompts = '\n\n'.join([f'<doc>\n{result}\n</docs>' for result in results])
        prompt = prompts['chat-with-docs'].format(
            QUESTION=message, DOCS=_docs_prompts
        )
    else:
        prompt = prompts['chat']
    history.append(HumanMessage(prompt))

    response: AIMessage = await llm_client.ainvoke(history)
    history.append(response)
    await dump_history(chat_id, history)
    return response.content
