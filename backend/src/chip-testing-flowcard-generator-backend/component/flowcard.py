import os
import json
import aiofiles
from typing import Sequence
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from config import const_config, common_config
from schema.flowcard import Flowcard, Tests
from component import knowledge, vllm_model
from util import generate_unique_id

flowcard_path = os.path.join(const_config.flowcard_dir, 'flowcard.json')
prompts_dir = const_config.prompts_dir
flowcard_parser = PydanticOutputParser(pydantic_object=Flowcard)
tests_parser = PydanticOutputParser(pydantic_object=Tests)
prompts = {}

is_initialized = False

if not is_initialized:
    os.makedirs(const_config.flowcard_dir, exist_ok=True)
    if not os.path.isfile(flowcard_path):
        with open(flowcard_path, 'w', encoding='utf-8') as _f:
            json.dump({}, _f, indent=4, ensure_ascii=False)
    for _title in [
        'flowcard-guidance', 'flowcard-with-message', 'flowcard-with-tests', 'flowcard-get-tests-from-order'
    ]:
        with open(os.path.join(prompts_dir, f'{_title}.md'), 'r', encoding='utf-8') as _f:
            prompts[_title] = _f.read()
    __is_initialized = True


async def __get_tests_from_order_doc(doc_id: str) -> Tests:
    """从向量化后的订单文档中提取测试对象"""
    order = await knowledge.query_from_doc('筛选内容-筛选', doc_id, 1)
    order = order[0]
    prompt = PromptTemplate(
        template=prompts['flowcard-get-tests-from-order'],
        input_variables=['ORDER'],
        partial_variables={'FORMAT': tests_parser.get_format_instructions()}
    )
    chain = prompt | vllm_model.chat_llm_client | tests_parser

    if common_config.low_gpu_memory_mode:
        await vllm_model.wakeup('vllm-llm')
    tests: Tests = await chain.ainvoke({'ORDER': order})
    if common_config.low_gpu_memory_mode:
        await vllm_model.sleep('vllm-llm')

    return tests


async def get_flowcards() -> dict[str, Flowcard]:
    """获取所有的历史流程卡ID和对象"""
    async with aiofiles.open(flowcard_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    json_results: dict = json.loads(content)
    results = {}
    for _id, _json in json_results.items():
        results[_id] = Flowcard.model_validate(_json)
    return results


async def delete_flowcard(flowcard_id: str) -> bool:
    """删除指定的流程卡"""
    async with aiofiles.open(flowcard_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    json_flowcards = json.loads(content)

    if flowcard_id in json_flowcards:
        del json_flowcards[flowcard_id]
        async with aiofiles.open(flowcard_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(json_flowcards, indent=4, ensure_ascii=False))

    return True


async def geneate_flowcard(
        order_doc_id: str | None = None,
        order_message: str | None = None,
        chip_code: str | None = None,
        using_doc_ids: Sequence[str] = (),
        k: int = 10,
        reranking_k: int | None = None
) -> tuple[str, Flowcard]:
    """
    生成新流程卡，返回ID和流程卡对象
    必须至少提供order_doc_id或者order_message中的一者,order_doc_id优先
    如果未提供order_doc_id而提供了order_message，那么必须提供chip_code
    using_doc_ids内的文档ID对应的文档会参与到RAG检索中，留空则不进行RAG检索
    k: RAG在每个文档中查找k条语义最相关的内容
    reranking_k: RAG在每个文档中查找reranking_k条语义最相关的内容，重排序后取k条结果。如果为None，则不使用重排序（加快响应速度）
    """
    assert order_doc_id or order_message

    if order_doc_id:
        tests = await __get_tests_from_order_doc(order_doc_id)
        chip_code = tests.chip_code
        _tests_text = '\n'.join([_test.name for _test in tests.tests])
        if tests.note:
            _tests_text += f'\n{tests.note}'
        query = _tests_text
        prompt = PromptTemplate(
            template=prompts['flowcard-with-tests'],
            input_variables=['DOCS'],
            partial_variables={
                'CHIP_CODE': tests.chip_code,
                'TESTS': _tests_text,
                'GUIDANCE': prompts['flowcard-guidance'],
                'FORMAT': flowcard_parser.get_format_instructions()
            }
        )
    else:  # order_message
        assert chip_code
        query = order_message
        prompt = PromptTemplate(
            template=prompts['flowcard-with-message'],
            input_variables=['DOCS'],
            partial_variables={
                'CHIP_CODE': chip_code,
                'ORDER': order_message,
                'GUIDANCE': prompts['flowcard-guidance'],
                'FORMAT': flowcard_parser.get_format_instructions()
            }
        )

    if len(using_doc_ids) > 0:
        docs = await knowledge.query_from_docs(
            f'{chip_code} {query}',
            using_doc_ids,
            k,
            reranking_k
        )
        docs = '\n\n'.join([f'<doc>\n{result}\n</docs>' for result in docs])
    else:
        docs = ''

    chain = prompt | vllm_model.chat_llm_client | flowcard_parser

    if common_config.low_gpu_memory_mode:
        await vllm_model.wakeup('vllm-llm')
    flowcard: Flowcard = await chain.ainvoke({'DOCS': docs})
    if common_config.low_gpu_memory_mode:
        await vllm_model.sleep('vllm-llm')

    _flowcard_ids = [_flowcard['id'] for _flowcard in (await get_flowcards())]
    flowcard_id = generate_unique_id(unique_checking_sequence=_flowcard_ids)

    async with aiofiles.open(flowcard_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    json_flowcards = json.loads(content)
    json_flowcards[flowcard_id] = flowcard.model_dump()
    async with aiofiles.open(flowcard_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(json_flowcards, indent=4, ensure_ascii=False))

    return flowcard_id, flowcard
