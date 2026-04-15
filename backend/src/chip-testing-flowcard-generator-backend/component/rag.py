import os
import shutil
import logging
from typing import Literal
from pydantic import SecretStr
from pymilvus import MilvusClient
from langchain_ollama import OllamaEmbeddings

from config import const_config, embedding_model_config, reranking_model_config, milvus_config
from schema.milvus_collection import docs_schema
import util

logger = logging.getLogger(__name__)
is_initialized = False
storage_dir = os.path.join(const_config.storage_dir, 'rag')
temp_dir = os.path.join(const_config.temp_dir, 'rag')

milvus_client: MilvusClient | None = None
embeddings_model = OllamaEmbeddings(
    base_url=embedding_model_config.base_url,
    model=embedding_model_config.model
)


def __init_milvus_database():
    """初始化Milvus数据库"""
    # 连接Milvus
    global milvus_client
    logger.info('Connecting to Milvus server...')
    logger.debug('Milvus Server Info:')
    logger.debug('\tURL: %s', milvus_config.url)
    logger.debug('\tDatabase: %s', milvus_config.database)
    milvus_client = MilvusClient(
        uri=milvus_config.url,
        token=milvus_config.token,
        db_name=milvus_config.database,
        timeout=30
    )
    logger.info('Connected to Milvus server')

    # 检查数据库
    logger.info('Initializing database `%s`...', milvus_config.database)
    databases = milvus_client.list_databases()
    if milvus_config.database not in databases:
        logger.debug('\tCreating database `%s`...', milvus_config.database)
        milvus_client.create_database(db_name=milvus_config.database)
        logger.debug('\tDatabase `%s` created.', milvus_config.database)

    # 检查Collections
    collection_schemas = {
        'docs': docs_schema,
        # 'users': user_schema  # todo 多用户系统
    }
    collections = milvus_client.list_collections()
    for collection_name in collection_schemas:
        if collection_name not in collections:
            logger.debug('\tCreating collection `%s`...', collection_name)
            milvus_client.create_collection(
                collection_name=collection_name,
                schema=collection_schemas[collection_name]
            )
            logger.debug('\tCollection `%s` created.', collection_name)

    logger.info('Database `%s` initialized.', milvus_config.database)


async def __vectorize_chunks(chunk: str) -> list[float]:
    """
    向量化单个chunk
    :param chunk: chunk文本
    :return: 向量
    """
    return await embeddings_model.aembed_query(chunk)


async def vectorize_doc_to_db(
        doc_path: str,
        doc_type: Literal['image', 'pdf', 'markdown', 'txt']
) -> str:
    """
    向量化文档内容并保存至向量数据库
    :param doc_path: 文档路径
    :param doc_type: 文档类型
    :return: 文档ID
    """
    pass
    # file_id =
    # shutil.copyfile(doc_path, os.path.join(temp_dir, ))
    # if doc_type == 'image':



if not is_initialized:
    logger.info('Initializing Milvus client...')
    os.makedirs(os.path.join(const_config.storage_dir, 'rag'), exist_ok=True)
    os.makedirs(os.path.join(const_config.temp_dir, 'rag'), exist_ok=True)
    __init_milvus_database()
