"""配置管理器"""
import tomllib
from typing import Literal
from pydantic import BaseModel


class ConstConfig(BaseModel):
    """常量配置"""
    storage_dir: str = 'storage'  # 文件存储目录
    temp_dir: str = 'temp'  # 临时工作目录


class CommonConfig(BaseModel):
    """主程序配置"""
    listen_host: str = '0.0.0.0'
    listen_port: int = 9000
    log_dir: str = './log/'
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    log_rotation_days: int = 30


class ModelConfig(BaseModel):
    """模型连接配置"""
    base_url: str
    api_key: str
    model: str


class EmbeddingModelConfig(ModelConfig):
    """嵌入模型连接设置"""
    dimension: int


class MilvusConfig(BaseModel):
    """Milvus连接配置"""
    url: str
    token: str
    database: str = 'chip_testing_rag'
    chunk_size: int = 1200
    chunk_overlap: int = 200
    top_k: int = 4


is_config_loaded = False
const_config = ConstConfig()
common_config: CommonConfig | None = None
llm_model_config: ModelConfig | None = None
embedding_model_config: EmbeddingModelConfig | None = None
reranking_model_config: ModelConfig | None = None
milvus_config: MilvusConfig | None = None


def __load_config():
    """从配置文件加载配置"""
    global common_config, llm_model_config, embedding_model_config, reranking_model_config, milvus_config
    with open('config.toml', 'rb') as f:
        file_config = tomllib.load(f)
    common_config = CommonConfig(**file_config['common'])
    llm_model_config = ModelConfig(**file_config['model']['llm'])
    embedding_model_config = EmbeddingModelConfig(**file_config['model']['embedding'])
    reranking_model_config = ModelConfig(**file_config['model']['reranking'])
    milvus_config = MilvusConfig(**file_config['milvus'])


if not is_config_loaded:
    __load_config()
