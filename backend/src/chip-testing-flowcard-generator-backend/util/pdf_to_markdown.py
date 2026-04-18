"""利用Deepseek OCR对PDF文件进行OCR识别的模块"""
import os
import pdf_craft
from typing import Literal


def pdf_to_markdown(
        input_pdf_path: str,
        output_markdown_path: str,
        output_markdown_assets_dir: str | None = None,
        ocr_model_size: Literal['tiny', 'small', 'base', 'large', 'gundam'] = 'gundam',
        proxy_enabled: bool = False,
        http_proxy: str | None = None,
        https_proxy: str | None = None
):
    """
    将PDF转换为Markdown
    :param input_pdf_path: 输入PDF路径
    :param output_markdown_path: Markdown要输出到的路径
    :param output_markdown_assets_dir: Markdown的资源文件要输出到的目录，默认位于output_markdown_path同级目录的assets目录下
    :param ocr_model_size: OCR模型尺寸
    :param proxy_enabled: 是否启用代理以连接huggingface.co
    :param http_proxy: HTTP代理
    :param https_proxy: HTTPS代理
    """
    original_proxy_envs = {
        'HTTP_PROXY': None,
        'HTTPS_PROXY': None
    }  # 用于存储原来的环境变量

    # 如果启用了代理，则替换环境变量
    if proxy_enabled:
        original_proxy_envs['HTTP_PROXY'] = os.environ.get('HTTP_PROXY', None)
        original_proxy_envs['HTTPS_PROXY'] = os.environ.get('HTTPS_PROXY', None)
        os.environ['HTTP_PROXY'] = http_proxy
        os.environ['HTTPS_PROXY'] = https_proxy

    if not output_markdown_assets_dir:
        output_markdown_assets_dir = os.path.join(os.path.dirname(input_pdf_path), 'assets')
    pdf_craft.transform_markdown(
        pdf_path=input_pdf_path,
        markdown_path=output_markdown_path,
        markdown_assets_path=output_markdown_assets_dir,
        ocr_size=ocr_model_size
    )

    # 运行完毕，恢复环境变量
    if proxy_enabled:
        if original_proxy_envs['HTTP_PROXY'] is None:
            del os.environ['HTTP_PROXY']
        else:
            os.environ['HTTP_PROXY'] = str(original_proxy_envs['HTTP_PROXY'])
        if original_proxy_envs['HTTPS_PROXY'] is None:
            del os.environ['HTTPS_PROXY']
        else:
            os.environ['HTTPS_PROXY'] = str(original_proxy_envs['HTTPS_PROXY'])
