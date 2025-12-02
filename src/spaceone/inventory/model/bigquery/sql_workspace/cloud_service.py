from schematics.types import PolyModelType

from spaceone.inventory.libs.schema.cloud_service import (
    CloudServiceMeta,
    CloudServiceResource,
    CloudServiceResponse,
)
from spaceone.inventory.libs.schema.metadata.dynamic_field import (
    DateTimeDyField,
    TextDyField,
)
from spaceone.inventory.libs.schema.metadata.dynamic_layout import (
    ItemDynamicLayout,
    ListDynamicLayout,
    SimpleTableDynamicLayout,
)
from spaceone.inventory.model.bigquery.sql_workspace.data import *

"""
SQL Workspace
"""

# TAB - Bucket
dataset_details_meta = ItemDynamicLayout.set_fields(
    "Information",
    fields=[
        TextDyField.data_source("ID", "data.id"),
        TextDyField.data_source("Name", "data.name"),
        TextDyField.data_source("Location", "data.location"),
        DateTimeDyField.data_source("Creation Time", "data.creation_time"),
        DateTimeDyField.data_source("Last Modified Time", "data.last_modified_time"),
    ],
)

access_table_meta = SimpleTableDynamicLayout.set_fields(
    "Access",
    root_path="data.access",
    fields=[
        TextDyField.data_source("Role", "role"),
        TextDyField.data_source("Special Group", "special_group"),
        TextDyField.data_source("User by E-mail", "user_by_email"),
    ],
)

workspace_dataset_meta = ListDynamicLayout.set_layouts(
    "Dataset Details", layouts=[dataset_details_meta, access_table_meta]
)

big_query_workspace_meta = CloudServiceMeta.set_layouts(
    [
        workspace_dataset_meta,
    ]
)


class BigQueryGroupResource(CloudServiceResource):
    cloud_service_group = StringType(default="BigQuery")


class SQLWorkSpaceResource(BigQueryGroupResource):
    cloud_service_type = StringType(default="SQLWorkspace")
    data = ModelType(BigQueryWorkSpace)
    _metadata = ModelType(
        CloudServiceMeta, default=big_query_workspace_meta, serialized_name="metadata"
    )


class SQLWorkSpaceResponse(CloudServiceResponse):
    resource = PolyModelType(SQLWorkSpaceResource)
