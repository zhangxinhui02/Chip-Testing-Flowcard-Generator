"""Docs的表结构"""
from pymilvus import CollectionSchema, FieldSchema, DataType

primary_key = FieldSchema(
    name="id",
    dtype=DataType.INT64,
    is_primary=True,
    auto_id=True
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

doc_note = FieldSchema(
    name="doc_note",
    dtype=DataType.VARCHAR,
    max_length=255,
    description='Document note'
)

doc_status = FieldSchema(
    name="doc_status",
    dtype=DataType.INT8,
    description='Document status: 0=ok 1=creating 2=failed'
)

doc_is_built_in = FieldSchema(
    name="doc_is_built_in",
    dtype=DataType.BOOL,
    description='Is document built in'
)

dummy_vector = FieldSchema(
    name="dummy_vector",
    dtype=DataType.FLOAT_VECTOR,
    dim=2,
    description="Placeholder data used to adapt to Milvus's vectorization requirements"
)

docs_info_schema = CollectionSchema(
    fields=[primary_key, doc_title, doc_id, doc_note, doc_status, doc_is_built_in, dummy_vector],
    description="Documents info collection"
)
