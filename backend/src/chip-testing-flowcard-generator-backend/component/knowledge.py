import os
import shutil
import aiohttp
import logging
from typing import Literal, List
from pymilvus import AsyncMilvusClient
from langchain_ollama import OllamaEmbeddings

from config import const_config, embedding_model_config, reranking_model_config, milvus_config, pdf_craft_config
from schema.milvus_collection import docs_info_schema, doc_schema
from schema.knowledge import Doc
import task_manager
import util

logger = logging.getLogger(__name__)
is_initialized = False
storage_dir = os.path.join(const_config.storage_dir, 'rag')
temp_dir = os.path.join(const_config.temp_dir, 'rag')

milvus_client: AsyncMilvusClient | None = None
embeddings_model = OllamaEmbeddings(
    base_url=embedding_model_config.base_url,
    model=embedding_model_config.model
)


async def init_milvus_database():
    """初始化Milvus数据库"""
    logger.info('Initializing Milvus client...')
    os.makedirs(os.path.join(const_config.storage_dir, 'rag'), exist_ok=True)
    os.makedirs(os.path.join(const_config.temp_dir, 'rag'), exist_ok=True)
    # 连接Milvus
    global milvus_client
    logger.info('Connecting to Milvus server...')
    logger.debug('Milvus Server Info:')
    logger.debug('\tURL: %s', milvus_config.url)
    logger.debug('\tDatabase: %s', milvus_config.database)
    milvus_client = AsyncMilvusClient(
        uri=milvus_config.url,
        token=milvus_config.token,
        db_name=milvus_config.database,
        timeout=30
    )
    logger.info('Connected to Milvus server')

    # 检查数据库
    logger.info('Initializing database `%s`...', milvus_config.database)
    databases = await milvus_client.list_databases()
    if milvus_config.database not in databases:
        logger.debug('\tCreating database `%s`...', milvus_config.database)
        await milvus_client.create_database(db_name=milvus_config.database)
        logger.debug('\tDatabase `%s` created.', milvus_config.database)

    # 检查Collections
    collection_schemas = {
        'docs_info': docs_info_schema,
        # 'users': user_schema  # todo 多用户系统
    }
    collections = await milvus_client.list_collections()
    for collection_name in collection_schemas:
        if collection_name not in collections:
            logger.debug('\tCreating collection `%s`...', collection_name)
            await milvus_client.create_collection(
                collection_name=collection_name,
                schema=collection_schemas[collection_name]
            )
            # 创建索引
            _index_params = milvus_client.prepare_index_params()
            _index_params.add_index(
                field_name="dummy_vector",
                index_type="AUTOINDEX",
                metric_type="COSINE",
            )
            await milvus_client.create_index(
                collection_name=collection_name,
                index_params=_index_params,
            )
            logger.debug('\tCollection `%s` created.', collection_name)
        await milvus_client.load_collection(collection_name)

    # 移除无效的docs
    _failed_docs = await milvus_client.query(
        collection_name="docs_info",
        filter="doc_status != 0",
        output_fields=["doc_title", "doc_id"]
    )
    if len(_failed_docs) > 0:
        logger.warning('\tDeleting unavailable documents...')
        await milvus_client.delete(
            collection_name="docs_info",
            filter="doc_status != 0"
        )
        for _failed_doc in _failed_docs:
            try:
                await milvus_client.drop_collection(f'doc_{_failed_doc["doc_id"]}')
                logger.warning(
                    '\t\tUnavailable document `%s`(id: %s) deleted.', _failed_doc['doc_title'], _failed_doc['doc_id']
                )
            except Exception as e:
                logger.error(
                    '\t\tError while deleting unavailable document `%s`(id: %s)\n\t\tException: %s',
                    _failed_doc['doc_title'],
                    _failed_doc['doc_id'],
                    str(e)
                )

    # 加载内建文档


    logger.info('Database `%s` initialized.', milvus_config.database)


async def __vectorize_chunks(chunk: str) -> List[float]:
    """
    向量化单个chunk
    :param chunk: chunk文本
    :return: 向量
    """
    vector = await embeddings_model.aembed_query(chunk)
    return vector


async def __get_all_doc_ids() -> List[str]:
    """获取所有文档ID列表"""
    results = await milvus_client.query(
        collection_name="docs_info",
        filter="",
        output_fields=["doc_id"],
        limit=const_config.milvus_query_limit
    )
    return [doc['doc_id'] for doc in results]


async def vectorize_doc_to_db(
        doc_title: str,
        doc_path: str,
        doc_type: Literal['image', 'pdf', 'markdown', 'txt'],
        doc_note: str | None = None
) -> bool:
    """
    向量化文档内容并保存至向量数据库，此任务耗时较长，需要异步处理
    :param doc_title: 文档标题
    :param doc_path: 文档路径
    :param doc_type: 文档类型
    :param doc_note: 文档备注
    :return: 是否处理成功
    """
    # 随机生成doc_id
    doc_id = util.generate_unique_id(unique_checking_sequence=await __get_all_doc_ids())

    # 在docs Collection中新增记录并标记为创建中状态
    await milvus_client.insert(
        f'docs_info',
        {
            'doc_title': doc_title,
            'doc_id': doc_id,
            'doc_note': doc_note,
            'doc_status': 1,  # CREATING
            'doc_is_built_in': False,
            'dummy_vector': [.0, .0]
        }
    )

    # 将文件复制到持久存储中
    _original_file_name = os.path.basename(doc_path)
    storaged_file_path = os.path.join(storage_dir, f'{doc_id}-{_original_file_name}')
    shutil.copyfile(doc_path, storaged_file_path)

    # ----- 一些计算密集任务的协程接口 -----

    async def _image_to_pdf(input_image_path: str, output_pdf_path: str):
        _task = await task_manager.run_task(
            'COMMON',
            util.image_to_pdf,
            (input_image_path, output_pdf_path),
            doc_id
        )
        return _task.status == 'SUCCESS'

    async def _pdf_to_markdown(
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
                pdf_craft_config.proxy_enabled,
                pdf_craft_config.http_proxy,
                pdf_craft_config.https_proxy
            ),
            doc_id
        )
        return _task.status == 'SUCCESS'

    async def _slice_markdown_to_chunks(
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
            ),
            doc_id
        )
        return _task.status == 'SUCCESS'

    # ----------

    async def _chunks_to_db(chunks_dir: str):
        """将指定目录内的所有chunks分片向量化并存储到到知识库内"""
        # 创建文档的Milvus Collection
        await milvus_client.create_collection(
            f'doc_{doc_id}',
            schema=doc_schema
        )
        # 向量化所有chunks并入库
        for _id, chunk in enumerate(os.listdir(chunks_dir)):
            with open(os.path.join(_tmp_chunks_dir, chunk), 'r', encoding='utf-8') as f:
                content = f.read()
            vector = await __vectorize_chunks(content)
            await milvus_client.insert(
                f'doc_{doc_id}',
                {
                    'id': _id + 1,
                    'content': content,
                    'vector': vector
                }
            )
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
        await milvus_client.delete(
            f'docs_info',
            filter=f'doc_id == "{doc_id}"'
        )
        await milvus_client.insert(
            f'docs_info',
            {
                'doc_title': doc_title,
                'doc_id': doc_id,
                'doc_note': doc_note,
                'doc_status': 0,  # OK
                'doc_is_built_in': False,
                'dummy_vector': [.0, .0]
            }
        )

    async def _error():
        # 发生错误，修改docs记录中的状态为失败
        await milvus_client.delete(
            f'docs_info',
            filter=f'doc_id == "{doc_id}"'
        )
        await milvus_client.insert(
            f'docs_info',
            {
                'doc_title': doc_title,
                'doc_id': doc_id,
                'doc_note': doc_note,
                'doc_status': 2,  # FAILED
                'doc_is_built_in': False,
                'dummy_vector': [.0, .0]
            }
        )

    is_preprocess_ok = False  # 存储所有流程的完成状态
    tmp_path = []  # 存储待清理的临时文件和目录

    # 图片：先转PDF，再转markdown，最后分片
    if doc_type == 'image':
        _input_image_path = storaged_file_path
        _tmp_pdf_path = os.path.join(temp_dir, f'{doc_id}.pdf')
        _tmp_markdown_path = os.path.abspath(os.path.join(temp_dir, f'{doc_id}.md'))
        _tmp_markdown_assets_dir = f'{doc_id}-assets/'
        _tmp_chunks_dir = os.path.abspath(os.path.join(temp_dir, f'{doc_id}-chunks/'))
        tmp_path.extend([
            _tmp_pdf_path, _tmp_markdown_path, os.path.join(temp_dir, _tmp_markdown_assets_dir), _tmp_chunks_dir
        ])

        if await _image_to_pdf(_input_image_path, _tmp_pdf_path):
            if await _pdf_to_markdown(_tmp_pdf_path, _tmp_markdown_path, _tmp_markdown_assets_dir):
                if await _slice_markdown_to_chunks(doc_title, _tmp_markdown_path, _tmp_chunks_dir):
                    is_preprocess_ok = True

    # PDF：先转markdown，再分片
    elif doc_type == 'pdf':
        _input_pdf_path = storaged_file_path
        _tmp_markdown_path = os.path.abspath(os.path.join(temp_dir, f'{doc_id}.md'))
        _tmp_markdown_assets_dir = f'{doc_id}-assets/'
        _tmp_chunks_dir = os.path.abspath(os.path.join(temp_dir, f'{doc_id}-chunks/'))
        tmp_path.extend([
            _tmp_markdown_path, os.path.join(temp_dir, _tmp_markdown_assets_dir), _tmp_chunks_dir
        ])

        if await _pdf_to_markdown(_input_pdf_path, _tmp_markdown_path, _tmp_markdown_assets_dir):
            if await _slice_markdown_to_chunks(doc_title, _tmp_markdown_path, _tmp_chunks_dir):
                is_preprocess_ok = True

    # markdown：直接分片
    elif doc_type == 'markdown':
        _input_markdown_path = os.path.abspath(storaged_file_path)
        _tmp_chunks_dir = os.path.abspath(os.path.join(temp_dir, f'{doc_id}-chunks/'))
        tmp_path.extend([
            _tmp_chunks_dir
        ])

        if await _slice_markdown_to_chunks(doc_title, _input_markdown_path, _tmp_chunks_dir):
            is_preprocess_ok = True

    # TXT：待补充
    else:  # txt
        _tmp_chunks_dir = ''
        # todo txt支持
        pass

    # 全部流程都成功，向量化chunks并入库，标记文档可用；否则标记文档处理失败
    if is_preprocess_ok:
        await _chunks_to_db(_tmp_chunks_dir)
    else:
        await _error()

    # 清理临时文件
    for _path in tmp_path:
        if os.path.isfile(_path):
            os.remove(_path)
        elif os.path.isdir(_path):
            shutil.rmtree(_path)
        else:
            logger.error('Failed to delete unknown temporary path: %s', _path)

    return is_preprocess_ok


async def get_all_docs() -> List[Doc]:
    """获取所有文档描述对象"""
    docs = []
    records = await milvus_client.query(
        collection_name="docs_info",
        filter="",
        limit=const_config.milvus_query_limit
    )
    for record in records:
        _status: Literal['ok', 'creating', 'failed'] = 'ok'
        if record["doc_status"] == 0:
            _status = 'ok'
        elif record["doc_status"] == 1:
            _status = 'creating'
        else:  # 3
            _status = 'failed'

        docs.append(
            Doc(
                title=record["doc_title"],
                id=record["doc_id"],
                status=_status,
                note=record["doc_note"],
                is_built_in=record["doc_is_built_in"]
            )
        )
    return docs


async def delete_doc(doc_id: str) -> bool:
    """删除指定文档ID对应的文档"""
    record = await milvus_client.query(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"',
        limit=const_config.milvus_query_limit
    )
    record = record[0]
    if record['doc_is_built_in']:
        return False

    await milvus_client.delete(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"'
    )
    await milvus_client.drop_collection(f'doc_{doc_id}')
    return True


async def update_doc_info(doc_id: str, new_doc_title: str, new_doc_note: str) -> bool:
    """修改文档的信息"""
    record = await milvus_client.query(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"',
        limit=const_config.milvus_query_limit
    )
    record = record[0]

    await milvus_client.delete(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"'
    )
    await milvus_client.insert(
        f'docs_info',
        {
            'doc_title': new_doc_title,
            'doc_id': record["doc_id"],
            'doc_note': new_doc_note,
            'doc_status': record['doc_status'],
            'doc_is_built_in': record['doc_is_built_in'],
            'dummy_vector': record['dummy_vector']
        }
    )
    return True


async def __rerank(query: str, docs: list[str], k: int = 10) -> list[str]:
    """传入查询文本和文档列表，返回排序后的最相关的k条记录"""
    assert k > 0, '`k` must be greater than 0'
    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{reranking_model_config.base_url.rstrip('/')}/api/rerank",
                json={
                    "model": reranking_model_config.model,
                    "query": query,
                    "documents": docs
                }
        ) as resp:
            result = await resp.json()

            reranked_docs = []
            for index, record in enumerate(result['results']):
                if index >= k:
                    break
                reranked_docs.append(docs[record['index']])

            return reranked_docs


async def query_from_doc(query: str, doc_id: str, k: int = 10, reranking_k: int | None = None) -> List[str]:
    """在指定文档中查找k条语义最相关的内容。如果指定了reranking_k参数，则按照此参数查找并返回重排序后的k条结果。"""
    assert (bool(reranking_k) is False) or (reranking_k <= k), '`reranking_k` must be greater than `k`.'
    vector = await embeddings_model.aembed_query(query)
    await milvus_client.load_collection(f'doc_{doc_id}')
    results = await milvus_client.search(
        collection_name=f"doc_{doc_id}",
        data=[vector],
        anns_field="vector",
        param={"metric_type": "COSINE"},
        limit=reranking_k if reranking_k else k,
        output_fields=["content"]
    )
    await milvus_client.release_collection(f'doc_{doc_id}')
    results = [result['content'] for result in results[0]]

    if reranking_k:
        results = await __rerank(query, results, k)

    return results


async def query_from_docs(query: str, doc_ids: List[str], k: int = 10, reranking_k: int | None = None) -> List[str]:
    """
    在指定的若干个文档中分别查找k条语义最相关的内容，最后返回所有结果中最相关的k条内容。
    如果指定了reranking_k参数，则按照此参数查找并返回重排序后的k条结果。
    """
    assert (bool(reranking_k) is False) or (reranking_k <= k), '`reranking_k` must be greater than `k`.'
    results = []
    for doc_id in doc_ids:
        results.extend(await query_from_doc(query, doc_id, k))
    results = await __rerank(query, results, k)
    return results
