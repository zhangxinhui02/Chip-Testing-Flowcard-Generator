"""利用Deepseek OCR对PDF文件进行OCR识别的模块"""
import os
import pdf_craft


def pdf_to_markdown(input_pdf_path: str, output_markdown_path: str, output_markdown_assets_dir: str | None = None):
    """
    将PDF转换为Markdown
    :param input_pdf_path: 输入PDF路径
    :param output_markdown_path: Markdown要输出到的路径
    :param output_markdown_assets_dir: Markdown的资源文件要输出到的目录，默认位于output_markdown_path同级目录的assets目录下
    """
    if not output_markdown_assets_dir:
        output_markdown_assets_dir = os.path.join(os.path.dirname(input_pdf_path), 'assets')
    pdf_craft.transform_markdown(
        pdf_path=input_pdf_path,
        markdown_path=output_markdown_path,
        markdown_assets_path=output_markdown_assets_dir,
    )
