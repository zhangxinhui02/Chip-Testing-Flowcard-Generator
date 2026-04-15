from .docs import router as docs_router
from .flowcards import router as flowcard_router
from .qa import router as qa_router

__all__ = [
    docs_router,
    flowcard_router,
    qa_router
]
