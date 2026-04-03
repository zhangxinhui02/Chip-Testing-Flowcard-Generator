"""将图片转换为PDF的模块，用于后续OCR识别"""
import img2pdf


def image_to_pdf(input_image_path: str, output_pdf_path: str):
    """
    将图片转换为PDF
    :param input_image_path: 输入图片路径
    :param output_pdf_path: PDF要输出到的路径
    """
    with open(output_pdf_path, "wb") as f:
        f.write(img2pdf.convert(input_image_path))
