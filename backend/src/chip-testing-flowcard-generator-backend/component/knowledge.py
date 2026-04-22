import os
import shutil
import logging
from pymilvus import AsyncMilvusClient
from typing import Literal, List, Sequence

from config import const_config, milvus_config
from schema.milvus_collection import docs_info_schema
import component.knowledge_helper as helper
from component import vllm_model
from schema.knowledge import Doc
import util

logger = logging.getLogger(__name__)
is_initialized = False
built_in_docs_dir = const_config.built_in_docs_dir
storage_dir = os.path.join(const_config.storage_dir, 'knowledge')
temp_dir = os.path.join(const_config.temp_dir, 'knowledge')

built_in_docs_map = {}
milvus_client: AsyncMilvusClient | None = None


async def init_milvus_database():
    """初始化Milvus数据库"""
    logger.info('Initializing Milvus client...')
    os.makedirs(built_in_docs_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
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

    # 初始化helper模块
    helper.init_helper(milvus_client)

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
    built_in_doc_titles = []
    for _title in os.listdir(built_in_docs_dir):
        if os.path.isdir(os.path.join(built_in_docs_dir, _title)):
            built_in_doc_titles.append(_title)
    if len(built_in_doc_titles) > 0:
        _exist_built_in_docs = await milvus_client.query(
            collection_name="docs_info",
            filter=f'doc_title in {str(built_in_doc_titles)}',
            output_fields=["doc_title", "doc_id"]
        )
        _exist_built_in_docs = [_record['doc_title'] for _record in _exist_built_in_docs]
        for _doc_title in built_in_doc_titles:
            if _doc_title not in _exist_built_in_docs:
                await vectorize_doc_to_db(
                    _doc_title,
                    os.path.join(built_in_docs_dir, _doc_title, 'chunks'),
                    'chunks',
                    '',
                    True
                )
    global built_in_docs_map
    _exist_built_in_docs = await milvus_client.query(
        collection_name="docs_info",
        filter="doc_is_built_in == true",
        output_fields=["doc_title", "doc_id"]
    )
    for _doc in _exist_built_in_docs:
        built_in_docs_map[_doc['doc_id']] = _doc['doc_title']

    logger.info('Database `%s` initialized.', milvus_config.database)


async def vectorize_doc_to_db(
        doc_title: str,
        doc_path: str,
        doc_type: Literal['image', 'pdf', 'markdown', 'txt', 'chunks'],
        doc_note: str = '',
        doc_is_built_in: bool = False
) -> bool:
    """
    向量化文档内容并保存至向量数据库，此任务耗时较长，需要异步处理
    :param doc_title: 文档标题
    :param doc_path: 文档路径
    :param doc_type: 文档类型
    :param doc_note: 文档备注
    :param doc_is_built_in: 文档是否为内建文档
    :return: 是否处理成功
    """
    # 随机生成doc_id
    doc_id = util.generate_unique_id(unique_checking_sequence=await helper.get_all_doc_ids())

    # 在docs Collection中新增记录并标记为创建中状态
    await milvus_client.insert(
        f'docs_info',
        {
            'doc_title': doc_title,
            'doc_id': doc_id,
            'doc_note': doc_note,
            'doc_status': 1,  # CREATING
            'doc_is_built_in': doc_is_built_in,
            'dummy_vector': [.0, .0]
        }
    )

    is_preprocess_ok = False  # 存储所有流程的完成状态
    tmp_path = []  # 存储待清理的临时文件和目录

    if not doc_is_built_in:
        # 将文件复制到持久存储中
        _original_file_name = os.path.basename(doc_path)
        storaged_file_path = os.path.join(storage_dir, f'{doc_id}-{_original_file_name}')
        shutil.copyfile(doc_path, storaged_file_path)

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

            if await helper.a_image_to_pdf(_input_image_path, _tmp_pdf_path):
                if await helper.a_pdf_to_markdown(_tmp_pdf_path, _tmp_markdown_path, _tmp_markdown_assets_dir):
                    if await helper.a_slice_markdown_to_chunks(doc_title, _tmp_markdown_path, _tmp_chunks_dir):
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

            if await helper.a_pdf_to_markdown(_input_pdf_path, _tmp_markdown_path, _tmp_markdown_assets_dir):
                if await helper.a_slice_markdown_to_chunks(doc_title, _tmp_markdown_path, _tmp_chunks_dir):
                    is_preprocess_ok = True

        # markdown：直接分片
        elif doc_type == 'markdown':
            _input_markdown_path = os.path.abspath(storaged_file_path)
            _tmp_chunks_dir = os.path.abspath(os.path.join(temp_dir, f'{doc_id}-chunks/'))
            tmp_path.extend([
                _tmp_chunks_dir
            ])

            if await helper.a_slice_markdown_to_chunks(doc_title, _input_markdown_path, _tmp_chunks_dir):
                is_preprocess_ok = True

        # TXT：待补充
        else:  # txt
            _tmp_chunks_dir = ''
            # todo txt支持
            pass

    # 如果doc_is_built_in，则输入必为chunks：直接向量化并入库
    else:
        _tmp_chunks_dir = doc_path
        is_preprocess_ok = True

    # 全部流程都成功，向量化chunks并入库，标记文档可用；否则标记文档处理失败
    if is_preprocess_ok:
        await helper.chunks_to_db(_tmp_chunks_dir, doc_id)
    else:
        await helper.error(doc_id)

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
    if doc_id in built_in_docs_map:
        return False

    await milvus_client.delete(
        collection_name="docs_info",
        filter=f'doc_id == "{doc_id}"'
    )
    await milvus_client.drop_collection(f'doc_{doc_id}')
    return True


async def update_doc_info(doc_id: str, new_doc_title: str, new_doc_note: str) -> bool:
    """修改文档的信息"""
    if doc_id in built_in_docs_map:
        if new_doc_title != built_in_docs_map[doc_id]:
            return False  # 内建文档不允许修改标题

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


async def query_from_doc(query: str, doc_id: str, k: int = 10, reranking_k: int | None = None) -> List[str]:
    """在指定文档中查找k条语义最相关的内容。如果指定了reranking_k参数，则按照此参数查找并返回重排序后的k条结果。"""
    assert (bool(reranking_k) is False) or (reranking_k >= k), '`reranking_k` must be equal or greater than `k`.'
    vector = await vllm_model.embedding_query(query)
    # todo: Collection的加载和释放需要锁
    await milvus_client.load_collection(f'doc_{doc_id}')
    results = await milvus_client.search(
        collection_name=f"doc_{doc_id}",
        data=[vector],
        anns_field="vector",
        search_params={"metric_type": "COSINE"},
        limit=reranking_k if reranking_k else k,
        output_fields=["content"]
    )
    results = [result['content'] for result in results[0]]
    await milvus_client.release_collection(f'doc_{doc_id}')

    if reranking_k:
        results = await vllm_model.reranker_query(query, results, k)

    return results


async def query_from_docs(query: str, doc_ids: Sequence[str], k: int = 10, reranking_k: int | None = None) -> List[str]:
    """
    在指定的若干个文档中分别查找k条语义最相关的内容，最后返回所有结果。
    如果指定了reranking_k参数，则按照此参数查找所有结果并返回重排序后的k条结果。
    """
    assert (bool(reranking_k) is False) or (reranking_k >= k), '`reranking_k` must be greater than `k`.'
    results = []
    for doc_id in set(doc_ids):
        results.extend(await query_from_doc(query, doc_id, reranking_k if reranking_k else k))
    if reranking_k:
        results = await vllm_model.reranker_query(query, results, k)
    return results
