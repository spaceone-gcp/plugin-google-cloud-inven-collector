from schematics.types import ModelType, PolyModelType, StringType

from spaceone.inventory.libs.schema.cloud_service import (
    CloudServiceMeta,
    CloudServiceResource,
    CloudServiceResponse,
)
from spaceone.inventory.libs.schema.metadata.dynamic_field import (
    DateTimeDyField,
    EnumDyField,
    TextDyField,
)
from spaceone.inventory.libs.schema.metadata.dynamic_layout import (
    ItemDynamicLayout,
)
from spaceone.inventory.model.storage_transfer.transfer_operation.data import (
    TransferOperation,
)

"""
Transfer Operation
"""

# TAB - Operation Configuration
operation_configuration_meta = ItemDynamicLayout.set_fields(
    "Configuration",
    fields=[
        TextDyField.data_source("Operation Name", "data.name"),
        TextDyField.data_source("Transfer Job", "data.transfer_job_name"),
        EnumDyField.data_source(
            "Status",
            "data.metadata.status",
            default_state={
                "safe": ["SUCCESS"],
                "warning": ["IN_PROGRESS", "PAUSED", "QUEUED", "SUSPENDING"],
                "alert": ["FAILED", "ABORTED"],
            },
        ),
        EnumDyField.data_source(
            "Done",
            "data.done",
            default_badge={"indigo.500": ["true"], "coral.600": ["false"]},
        ),
        DateTimeDyField.data_source("Start Time", "data.metadata.start_time"),
        DateTimeDyField.data_source("End Time", "data.metadata.end_time"),
        TextDyField.data_source("Duration", "data.duration"),
    ],
)

transfer_operation_meta = CloudServiceMeta.set_layouts(
    [
        operation_configuration_meta,
    ]
)


class StorageTransferResource(CloudServiceResource):
    cloud_service_group = StringType(default="StorageTransfer")


class TransferOperationResource(StorageTransferResource):
    cloud_service_type = StringType(default="TransferOperation")
    data = ModelType(TransferOperation)
    _metadata = ModelType(
        CloudServiceMeta, default=transfer_operation_meta, serialized_name="metadata"
    )


class TransferOperationResponse(CloudServiceResponse):
    resource = PolyModelType(TransferOperationResource)
