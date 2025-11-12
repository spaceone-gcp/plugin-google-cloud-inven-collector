from schematics.types import ModelType, PolyModelType, StringType

from spaceone.inventory.libs.schema.cloud_service import (
    CloudServiceMeta,
    CloudServiceResource,
    CloudServiceResponse,
)
from spaceone.inventory.model.networking.vpc_gateway.cloud_service_type import (
    vpc_gateway_cloud_service_meta,
)
from spaceone.inventory.model.networking.vpc_gateway.data import VPCGateway

"""
VPC Gateway Cloud Service
"""


class VPCGatewayResource(CloudServiceResource):
    cloud_service_group = StringType(default="Networking")
    cloud_service_type = StringType(default="VPCGateway")
    data = ModelType(VPCGateway)
    _metadata = ModelType(
        CloudServiceMeta,
        default=vpc_gateway_cloud_service_meta,
        serialized_name="metadata",
    )


class VPCGatewayResponse(CloudServiceResponse):
    resource = PolyModelType(VPCGatewayResource)
