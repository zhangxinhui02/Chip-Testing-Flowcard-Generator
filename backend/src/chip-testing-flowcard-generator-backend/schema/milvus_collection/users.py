"""Users的表结构"""
from pymilvus import CollectionSchema, FieldSchema, DataType

primary_key = FieldSchema(
    name="user_id",
    dtype=DataType.INT64,
    is_primary=True,
)

user_name = FieldSchema(
    name="user_name",
    dtype=DataType.VARCHAR,
    max_length=255,
    description='User name'
)

password_hash = FieldSchema(
    name="password_hash",
    dtype=DataType.VARCHAR,
    max_length=255,
    description='Hashed user password'
)

dummy_vector = FieldSchema(
    name="dummy_vector",
    dtype=DataType.FLOAT_VECTOR,
    dim=2,
    description="Placeholder data used to adapt to Milvus's vectorization requirements"
)

user_schema = CollectionSchema(
    fields=[primary_key, user_name, password_hash, dummy_vector],
    description="User data collection"
)
