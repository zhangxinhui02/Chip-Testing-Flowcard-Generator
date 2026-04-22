from .docs import router as docs_router
from .flowcards import router as flowcard_router
from .chat import router as chat_router

__all__ = [
    docs_router,
    flowcard_router,
    chat_router
]
