"""Docs的表结构"""
from pymilvus import CollectionSchema, FieldSchema, DataType

primary_key = FieldSchema(
    name="id",
    dtype=DataType.INT64,
    is_primary=True,
)

doc_title = FieldSchema(
    name="doc_title",
    dtype=DataType.VARCHAR,
    max_length=255,
    description='Document title'
)

doc_id = FieldSchema(
    name="doc_id",
    dtype=DataType.VARCHAR,
    max_length=12,
    description='Document ID'
)

dummy_vector = FieldSchema(
    name="dummy_vector",
    dtype=DataType.FLOAT_VECTOR,
    dim=2,
    description="Placeholder data used to adapt to Milvus's vectorization requirements"
)

docs_schema = CollectionSchema(
    fields=[primary_key, doc_title, doc_id, dummy_vector],
    description="Document ID collection"
)
