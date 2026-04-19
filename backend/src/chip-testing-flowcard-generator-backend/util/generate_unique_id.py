import random
import string
from typing import Sequence

def generate_unique_id(length=8, unique_checking_sequence: Sequence = ()):
    """生成随机的ID，可选长度和唯一性验证"""
    chars = string.ascii_lowercase + string.digits  # a-z + 0-9
    result = ''.join(random.choices(chars, k=length))
    if result in unique_checking_sequence:
        return generate_unique_id(length=length, unique_checking_sequence=unique_checking_sequence)
    return result
