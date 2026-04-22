import json
import aiohttp
from typing import Literal
from pydantic import SecretStr
from langchain_openai import OpenAI, ChatOpenAI, OpenAIEmbeddings

from config import common_config, llm_model_config, embedding_model_config, reranker_model_config

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


def __resolv_vllm_host_port(vllm_instance: Literal['vllm-llm', 'vllm-embedding', 'vllm-reranker']) -> tuple[str, int]:
    """根据vllm实例的url，解析出主机名和端口"""
    if vllm_instance == 'vllm-llm':
        vllm_url = llm_model_config.base_url
    elif vllm_instance == 'vllm-embedding':
        vllm_url = embedding_model_config.base_url
    else:
        vllm_url = reranker_model_config.base_url

    if vllm_url.startswith('http://'):
        protocol = 'http://'
    elif vllm_url.startswith('https://'):
        protocol = 'https://'
    else:
        raise ValueError
    vllm_url = vllm_url.lstrip(protocol)

    vllm_url = vllm_url.split('/')[0]
    if ':' in vllm_url:
        vllm_url, vllm_port = vllm_url.split(':')[0], int(vllm_url.split(':')[1])
    else:
        vllm_port = 443 if protocol == 'https://' else 80

    return vllm_url, vllm_port


async def sleep(vllm_instance: Literal['vllm-llm', 'vllm-embedding', 'vllm-reranker']):
    """使指定的vllm实例对应的模型睡眠，释放显存"""
    host, port = __resolv_vllm_host_port(vllm_instance)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"http://{host}:{port}/sleep?level=1") as resp:
            resp.raise_for_status()


async def wakeup(vllm_instance: Literal['vllm-llm', 'vllm-embedding', 'vllm-reranker']):
    """唤醒指定的vllm实例对应的模型，占用显存"""
    host, port = __resolv_vllm_host_port(vllm_instance)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"http://{host}:{port}/wake_up") as resp:
            resp.raise_for_status()


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
            result = await resp.json()

    if common_config.low_gpu_memory_mode:
        await sleep('vllm-reranker')

    reranked_docs = []
    for record in result['results']:
        reranked_docs.append(docs[record['index']])
    return reranked_docs
