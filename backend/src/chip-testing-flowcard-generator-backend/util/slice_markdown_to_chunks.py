"""此模块将markdown按照标题切分为更小的chunks，供下一步向量化"""
import os
from typing import Literal
from langchain_text_splitters import MarkdownHeaderTextSplitter

def slice_markdown_to_chunks(
        input_markdown_path: str,
        output_chunks_dir: str,
        min_slice_markdown_level: Literal[1, 2, 3, 4, 5, 6] = 3
):
    """
    将markdown按照标题切分为更小的chunks
    :param input_markdown_path: 输入markdown路径
    :param output_chunks_dir: chunks要输出到的目录
    :param min_slice_markdown_level: 切分的最小markdown级别，默认为3（三级标题）
    :return:
    """
    markdown_headers = [
        ("#", "1"),
        ("##", "2"),
        ("###", "3"),
        ("####", "4"),
        ("#####", "5"),
        ("######", "6"),
    ]
    with open(input_markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=markdown_headers[:min_slice_markdown_level]
    )
    chunks = splitter.split_text(content)

    for i in range(len(chunks)):
        with open(os.path.join(output_chunks_dir, f'{i + 1}.md'), 'w', encoding='utf-8') as f:
            metadata = chunks[i].metadata
            content = ''
            for _level, _title in metadata.items():
                content += f'{"#" * int(_level)} {_title}\n'
            content += f'\n---\n\n{chunks[i].page_content}'
            f.write(content)
