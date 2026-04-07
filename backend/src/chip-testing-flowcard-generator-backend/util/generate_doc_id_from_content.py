import asyncio
import hashlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def _blake2_file_id_worker(file_path: str, digest_size: int = 32, chunk_size: int = 1024 * 1024) -> str:
    """
    在子进程中执行的同步函数，使用 BLAKE2b 对文件内容生成唯一ID
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    h = hashlib.blake2b(digest_size=digest_size)

    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)

    return h.hexdigest()


async def generate_doc_id_from_content(
        file_path: str,
        digest_size: int = 32,
        chunk_size: int = 1024 * 1024,
) -> str:
    """协程函数，在子进程中使用 BLAKE2b 对文件内容生成唯一ID"""
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(
            executor,
            _blake2_file_id_worker,
            file_path,
            digest_size,
            chunk_size,
        )
