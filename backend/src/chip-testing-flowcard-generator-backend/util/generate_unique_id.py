import random
import string

def generate_unique_id(length=8, unique_checking_sequence: list | tuple | None = None):
    """生成随机的ID，可选长度和唯一性验证"""
    chars = string.ascii_lowercase + string.digits  # a-z + 0-9
    result = ''.join(random.choices(chars, k=length))
    if unique_checking_sequence and result in unique_checking_sequence:
        return generate_unique_id(length=length, unique_checking_sequence=unique_checking_sequence)
    return result
