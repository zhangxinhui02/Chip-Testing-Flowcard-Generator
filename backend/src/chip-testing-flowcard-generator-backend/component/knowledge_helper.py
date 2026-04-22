"""knowledge模块的辅助模块，包含一些底层处理函数"""
import os
import logging
from typing import Literal, List
from pymilvus import AsyncMilvusClient

from config import const_config, common_config, pdf_craft_config
from schema.milvus_collection import doc_schema
from component import vllm_model
import task_manager
import util

logger = logging.getLogger(__name__)
milvus_client: AsyncMilvusClient | None = None


def init_helper(_milvus_client: AsyncMilvusClient):
    """初始化辅助模块"""
    global milvus_client
    milvus_client = _milvus_client


# ----- 一些计算密集型任务的协程接口 -----

async def a_image_to_pdf(input_image_path: str, output_pdf_path: str):
    _task = await task_manager.run_task(
        'COMMON',
        util.image_to_pdf,
        (input_image_path, output_pdf_path)
    )
    return _task.status == 'SUCCESS'


async def a_pdf_to_markdown(
        input_pdf_path: str,
        output_markdown_path: str,
        output_markdown_assets_dir: str | None = None
):
    _task = await task_manager.run_task(
        'GPU',
        util.pdf_to_markdown,
        (
            input_pdf_path,
            output_markdown_path,
            output_markdown_assets_dir,
            pdf_craft_config.ocr_model_size,
            pdf_craft_config.proxy_enabled,
            pdf_craft_config.http_proxy,
            pdf_craft_config.https_proxy
        )
    )
    return _task.status == 'SUCCESS'


async def a_slice_markdown_to_chunks(
        title: str,
        input_markdown_path: str,
        output_chunks_dir: str,
        min_slice_markdown_level: Literal[1, 2, 3, 4, 5, 6] = 3
):
    _task = await task_manager.run_task(
        'COMMON',
        util.slice_markdown_to_chunks,
        (
            title,
            input_markdown_path,
            output_chunks_dir,
            min_slice_markdown_level
        )
    )
    return _task.status == 'SUCCESS'


# ----------

async def get_all_doc_ids() -> List[str]:
    """获取所有文档ID列表"""
    results = await milvus_client.query(
        collection_name="docs_info",
        filter="",
        output_fields=["doc_id"],
        limit=const_config.milvus_query_limit
    )
    return [doc['doc_id'] for doc in results]


async def chunks_to_db(chunks_dir: str, doc_id: str):
    """将指定目录内的所有chunks分片向量化并存储到到知识库内"""
    # 创建文档的Milvus Collection
    await milvus_client.create_collection(
        f'doc_{doc_id}',
        schema=doc_schema
    )
    # 向量化所有chunks并入库
    if common_config.low_gpu_memory_mode:
        await vllm_model.wakeup('vllm-embedding')
    chunk_files = os.listdir(chunks_dir)
    _length = len(chunk_files)
    for _id, chunk_file in enumerate(chunk_files):
        logger.info('Processing chunk [%s/%s]', _id + 1, _length)
        with open(os.path.join(chunks_dir, chunk_file), 'r', encoding='utf-8') as f:
            content = f.read()
        vector = await vllm_model.embedding_client.aembed_query(content)
        await milvus_client.insert(
            f'doc_{doc_id}',
            {
                'id': _id + 1,
                'content': content,
                'vector': vector
            }
        )
    if common_config.low_gpu_memory_mode:
        await vllm_model.sleep('vllm-embedding')
    # 建立索引
    index_params = milvus_client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 1024}
    )
    await milvus_client.create_index(
        collection_name=f"doc_{doc_id}",
        index_params=index_params
    )
    # 修改docs记录中的状态为OK
    record = await milvus_client.query(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"'
    )
    record = record[0]
    await milvus_client.delete(
        f'docs_info',
        filter=f'doc_id == "{doc_id}"'
    )
    await milvus_client.insert(
        f'docs_info',
        {
            'doc_title': record['doc_title'],
            'doc_id': doc_id,
            'doc_note': record['doc_note'],
            'doc_status': 0,  # OK
            'doc_is_built_in': record['doc_is_built_in'],
            'dummy_vector': [.0, .0]
        }
    )


async def error(doc_id: str):
    """发生错误，修改docs记录中的状态为失败"""
    record = await milvus_client.query(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"'
    )
    record = record[0]
    await milvus_client.delete(
        f'docs_info',
        filter=f'doc_id == "{doc_id}"'
    )
    await milvus_client.insert(
        f'docs_info',
        {
            'doc_title': record['doc_title'],
            'doc_id': doc_id,
            'doc_note': record['doc_note'],
            'doc_status': 2,  # FAILED
            'doc_is_built_in': record['doc_is_built_in'],
            'dummy_vector': [.0, .0]
        }
    )
