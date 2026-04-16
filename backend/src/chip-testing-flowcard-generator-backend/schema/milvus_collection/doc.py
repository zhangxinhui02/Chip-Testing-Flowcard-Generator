"""Doc的表结构"""
from pymilvus import CollectionSchema, FieldSchema, DataType

from config import embedding_model_config

primary_key = FieldSchema(
    name="id",
    dtype=DataType.INT64,
    is_primary=True
)

content = FieldSchema(
    name="content",
    dtype=DataType.VARCHAR,
    max_length=10000,
    description='Chunk content'
)

vector = FieldSchema(
    name="vector",
    dtype=DataType.FLOAT_VECTOR,
    dim=embedding_model_config.dimension,
    description='Chunk vector'
)

docs_schema = CollectionSchema(
    fields=[primary_key, content, vector],
    description="Document vector collection"
)
