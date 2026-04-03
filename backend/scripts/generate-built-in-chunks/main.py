"""此脚本用于从PDF文档生成Markdown文档和可被向量化的分块chunks"""
import os
import pdf_craft
from langchain_text_splitters import MarkdownHeaderTextSplitter

INPUT_PDF_PATH = './target.pdf'
OUTPUT_MARKDOWN_PATH = './target.md'
OUTPUT_MARKDOWN_ASSETS_DIR = './assets/'
OUTPUT_CHUNKS_DIR = './chunks/'

os.makedirs(os.path.dirname(OUTPUT_MARKDOWN_PATH), exist_ok=True)
os.makedirs(OUTPUT_MARKDOWN_ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_CHUNKS_DIR, exist_ok=True)

pdf_craft.transform_markdown(
    pdf_path=INPUT_PDF_PATH,
    markdown_path=OUTPUT_MARKDOWN_PATH,
    markdown_assets_path=OUTPUT_MARKDOWN_ASSETS_DIR,
)

with open(OUTPUT_MARKDOWN_PATH, 'r', encoding='utf-8') as f:
    content = f.read()
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[  # 按需选择最小切分层级
        ("#", "1"),
        ("##", "2"),
        ("###", "3"),
        # ("####", "4"),
        # ("#####", "5"),
        # ("######", "6"),
    ]
)
chunks = splitter.split_text(content)

# 调试用，将chunks按上下文长度上下文从大到小排序
# target = []
# for chunk in chunks:
#     target.append((len(chunk.page_content), chunk))
# target.sort(key=lambda x: x[0], reverse=True)

for i in range(len(chunks)):
    with open(os.path.join(OUTPUT_CHUNKS_DIR, f'{i + 1}.md'), 'w', encoding='utf-8') as f:
        metadata = chunks[i].metadata
        content = ''
        for _level, _title in metadata.items():
            content += f'{"#" * int(_level)} {_title}\n'
        content += f'\n---\n\n{chunks[i].page_content}'
        f.write(content)
