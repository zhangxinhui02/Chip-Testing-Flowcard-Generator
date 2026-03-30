from langchain_milvus import Milvus

from config import llm_model_config, embedding_model_config, reranking_model_config, milvus_config
from client.milvus_client import MilvusClient

milvus_client: Milvus | None = None

def init_knowledge_db():
    """初始化RAG知识库"""
    # 检查Milvus数据库连接
    pass
    # 检查数据库是否存在
    pass
    # 检查元数据表是否存在
    # doc
    # user
    #
    # 遍历本地持久化文档，检查对应的文档知识库是否存在，如果不存在则创建
    pass
