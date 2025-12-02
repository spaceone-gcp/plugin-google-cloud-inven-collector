from schematics import Model
from schematics.types import ModelType, StringType

from spaceone.inventory.libs.schema.cloud_service import BaseResource
from spaceone.inventory.libs.schema.google_cloud_logging import (
    GoogleCloudLoggingModel,
)


class Display(Model):
    output_display = StringType(serialize_when_none=False, default="show")


class Schema(BaseResource):
    name = StringType(serialize_when_none=False)
    schema_type = StringType(
        choices=["TYPE_UNSPECIFIED", "PROTOCOL_BUFFER", "AVRO"],
        serialize_when_none=False,
    )
    definition = StringType(serialize_when_none=False)
    revision_id = StringType(serialize_when_none=False, deserialize_from="revisionId")
    revision_create_time = StringType(
        serialize_when_none=False, deserialize_from="revisionCreateTime"
    )
    display = ModelType(Display, serialize_when_none=False)
    # Logging data
    google_cloud_logging = ModelType(GoogleCloudLoggingModel, serialize_when_none=False)

    def reference(self):
        return {
            "resource_id": self.id,
            "external_link": f"https://console.cloud.google.com/cloudpubsub/schema/detail/{self.id}?project={self.project}",
        }


"""
{
  "name": string,
  "type": enum (Type),
  "definition": string,
  "revisionId": string,
  "revisionCreateTime": string
}
"""
