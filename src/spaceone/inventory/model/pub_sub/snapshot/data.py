from schematics.types import DictType, ModelType, StringType

from spaceone.inventory.libs.schema.cloud_service import BaseResource
from spaceone.inventory.libs.schema.google_cloud_monitoring import (
    GoogleCloudMonitoringModel,
)


class Snapshot(BaseResource):
    id = StringType(serialize_when_none=False)
    name = StringType(serialize_when_none=False)
    topic = StringType(serialize_when_none=False)
    expire_time = StringType(serialize_when_none=False, deserialize_from="expireTime")
    labels = DictType(StringType, serialize_when_none=False)
    # Monitoring data
    google_cloud_monitoring = ModelType(
        GoogleCloudMonitoringModel, serialize_when_none=False
    )

    def reference(self):
        return {
            "resource_id": self.id,
            "external_link": f"https://console.cloud.google.com/cloudpubsub/snapshot/detail/{self.id}?project={self.project}",
        }
