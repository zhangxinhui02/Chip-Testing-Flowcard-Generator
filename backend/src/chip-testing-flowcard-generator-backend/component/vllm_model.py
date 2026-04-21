import json
import aiohttp
from typing import Literal
from pydantic import SecretStr
from langchain_openai import OpenAI, ChatOpenAI, OpenAIEmbeddings

from config import common_config, llm_model_config, embedding_model_config, reranker_model_config

llm_client = OpenAI(
    api_key=SecretStr(llm_model_config.api_key),
    base_url=llm_model_config.base_url,
    model=llm_model_config.model,
    temperature=0.7
)
chat_llm_client = ChatOpenAI(
    api_key=SecretStr(llm_model_config.api_key),
    base_url=llm_model_config.base_url,
    model=llm_model_config.model,
    temperature=0.7
)
embedding_client = OpenAIEmbeddings(
    api_key=SecretStr(embedding_model_config.api_key),
    base_url=embedding_model_config.base_url,
    model=embedding_model_config.model
)


async def sleep(vllm_host: Literal['vllm-llm', 'vllm-embedding', 'vllm-reranker'], vllm_port: int = 8000):
    """使指定的vllm实例对应的模型睡眠，释放显存"""
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"http://{vllm_host}:{vllm_port}/sleep?level=1") as resp:
            resp.raise_for_status()


async def wakeup(vllm_host: Literal['vllm-llm', 'vllm-embedding', 'vllm-reranker'], vllm_port: int = 8000):
    """唤醒指定的vllm实例对应的模型，占用显存"""
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"http://{vllm_host}:{vllm_port}/wake_up") as resp:
            resp.raise_for_status()


async def llm_invoke(invoke_input):
    """调用OpenAI对象，按需唤醒或睡眠模型"""
    if common_config.low_gpu_memory_mode:
        await wakeup('vllm-llm')
    result = await llm_client.ainvoke(invoke_input)
    if common_config.low_gpu_memory_mode:
        await sleep('vllm-llm')
    return result


async def chat_llm_invoke(invoke_input):
    """调用ChatOpenAI对象，按需唤醒或睡眠模型"""
    if common_config.low_gpu_memory_mode:
        await wakeup('vllm-llm')
    result = await chat_llm_client.ainvoke(invoke_input)
    if common_config.low_gpu_memory_mode:
        await sleep('vllm-llm')
    return result


async def embedding_query(query_input):
    """调用OpenAIEmbeddings对象，按需唤醒或睡眠模型"""
    if common_config.low_gpu_memory_mode:
        await wakeup('vllm-embedding')
    result = await embedding_client.aembed_query(query_input)
    if common_config.low_gpu_memory_mode:
        await sleep('vllm-embedding')
    return result


async def reranker_query(query: str, docs: list[str], k: int = 10):
    """传入查询文本和文档列表，返回排序后的最相关的k条记录，按需唤醒或睡眠模型"""
    assert k > 0, '`k` must be greater than 0'

    if common_config.low_gpu_memory_mode:
        await wakeup('vllm-reranker')

    payload = {
        "model": reranker_model_config.model,
        "query": query,
        "documents": docs,
        "top_n": k
    }
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"{reranker_model_config.base_url.rstrip('/')}/rerank", json=payload) as resp:
            resp.raise_for_status()
            json_content = await resp.json()
            result = json.loads(json_content)

    if common_config.low_gpu_memory_mode:
        await sleep('vllm-reranker')

    reranked_docs = []
    for record in result['results']:
        reranked_docs.append(docs[record['index']])
    return reranked_docs
