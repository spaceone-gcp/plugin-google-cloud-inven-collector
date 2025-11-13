import logging
from typing import Any, Dict, List, Tuple

from spaceone.inventory.connector.app_engine.instance_v1 import (
    AppEngineInstanceV1Connector,
)
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import (
    BaseResponse,
    log_state_summary,
    reset_state_counters,
)
from spaceone.inventory.libs.schema.cloud_service import ErrorResourceResponse
from spaceone.inventory.model.app_engine.instance.cloud_service import (
    AppEngineInstanceResource,
)
from spaceone.inventory.model.app_engine.instance.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.app_engine.instance.data import AppEngineInstance
from spaceone.inventory.model.kubernetes_engine.cluster.data import convert_datetime

_LOGGER = logging.getLogger(__name__)


def bytes_to_mb(bytes_value):
    """Convert bytes to MB."""
    if not bytes_value or bytes_value == 0:
        return 0.0
    return round(float(bytes_value) / (1024 * 1024), 1)


class AppEngineInstanceV1Manager(GoogleCloudManager):
    connector_name = "AppEngineInstanceV1Connector"
    cloud_service_types = CLOUD_SERVICE_TYPES
    cloud_service_group = "AppEngine"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_memory_usage(
        self, instance: Dict[str, Any], instance_id: str
    ) -> float:
        """Convert memory usage from bytes to MB."""
        memory_bytes = instance.get("memoryUsage", 0) or 0

        if not memory_bytes or memory_bytes == 0:
            return 0.0

        memory_mb = bytes_to_mb(memory_bytes)
        return memory_mb

    def _extract_request_count(self, instance: Dict[str, Any], instance_id: str) -> int:
        """Extract request count from instance data."""

        possible_fields = [
            "requests",
            "requestCount",
            "request_count",
            "totalRequests",
            "total_requests",
            "requestsCount",
            "numRequests",
            "num_requests",
        ]

        request_count = 0
        found_field = None

        for field_name in possible_fields:
            if field_name in instance:
                value = instance[field_name]
                if value is not None:
                    try:
                        request_count = int(value)
                        found_field = field_name
                        break
                    except (ValueError, TypeError):
                        continue

        if found_field is None:
            if "metrics" in instance:
                metrics = instance["metrics"]
                if isinstance(metrics, dict):
                    for field_name in possible_fields:
                        if field_name in metrics:
                            value = metrics[field_name]
                            if value is not None:
                                try:
                                    request_count = int(value)
                                    found_field = f"metrics.{field_name}"
                                    break
                                except (ValueError, TypeError):
                                    continue

        return request_count

    def list_instances(
        self, service_id: str, version_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """List App Engine instances (v1beta API).

        Args:
            service_id: Service ID.
            version_id: Version ID.
            params: Parameters dictionary for query.

        Returns:
            List of App Engine instances.

        Raises:
            Exception: When App Engine API call fails.
        """
        instance_connector: AppEngineInstanceV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            instances = instance_connector.list_instances(service_id, version_id)
            _LOGGER.info(
                f"Found {len(instances)} instances for version {version_id} (v1beta)"
            )
            return instances
        except Exception as e:
            _LOGGER.error(
                f"Failed to list instances for version {version_id} (v1beta): {e}"
            )
            return []

    def get_instance(
        self, service_id: str, version_id: str, instance_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get specific App Engine instance information (v1beta API).

        Args:
            service_id: Service ID.
            version_id: Version ID.
            instance_id: Instance ID.
            params: Parameters dictionary for query.

        Returns:
            App Engine instance information dictionary.

        Raises:
            Exception: When App Engine API call fails.
        """
        instance_connector: AppEngineInstanceV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            instance = instance_connector.get_instance(
                service_id, version_id, instance_id
            )
            if instance:
                _LOGGER.info(f"Retrieved instance {instance_id} (v1)")
            return instance or {}
        except Exception as e:
            _LOGGER.error(f"Failed to get instance {instance_id} (v1): {e}")
            return {}

    def list_all_instances(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all App Engine instances (v1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of all App Engine instances.

        Raises:
            Exception: When App Engine API call fails.
        """
        instance_connector: AppEngineInstanceV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            instances = instance_connector.list_all_instances()
            _LOGGER.info(f"Found {len(instances)} total AppEngine instances (v1)")
            return instances
        except Exception as e:
            _LOGGER.error(f"Failed to list all AppEngine instances (v1): {e}")
            return []

    def get_instance_metrics(
        self, service_id: str, version_id: str, instance_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get App Engine instance metrics (v1 API).

        Args:
            service_id: Service ID.
            version_id: Version ID.
            instance_id: Instance ID.
            params: Parameters dictionary for query.

        Returns:
            Instance metrics information dictionary.

        Raises:
            Exception: When App Engine API call fails.
        """
        instance_connector: AppEngineInstanceV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            metrics = instance_connector.get_instance_metrics(
                service_id, version_id, instance_id
            )
            return metrics or {}
        except Exception as e:
            _LOGGER.error(f"Failed to get metrics for instance {instance_id} (v1): {e}")
            return {}

    def get_instance_details(
        self, service_id: str, version_id: str, instance_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get App Engine instance details (v1 API).

        Args:
            service_id: Service ID.
            version_id: Version ID.
            instance_id: Instance ID.
            params: Parameters dictionary for query.

        Returns:
            Instance details information dictionary.

        Raises:
            Exception: When App Engine API call fails.
        """
        instance_connector: AppEngineInstanceV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            details = instance_connector.get_instance_details(
                service_id, version_id, instance_id
            )
            return details or {}
        except Exception as e:
            _LOGGER.error(f"Failed to get details for instance {instance_id} (v1): {e}")
            return {}

    def collect_cloud_service(
        self, params: Dict[str, Any]
    ) -> Tuple[List[Any], List[ErrorResourceResponse]]:
        """Collect App Engine instance information (v1 API).

        Args:
            params: Parameters dictionary for collection.

        Returns:
            Tuple of collected cloud service list and error response list.

        Raises:
            Exception: When data collection fails.
        """
        _LOGGER.debug("** AppEngine Instance V1Beta START **")

        reset_state_counters()

        collected_cloud_services = []
        error_responses = []

        secret_data = params["secret_data"]
        project_id = secret_data["project_id"]

        try:
            app_connector = self.locator.get_connector(
                "AppEngineApplicationV1Connector", **params
            )
            services = app_connector.list_services()

            for service in services:
                service_id = service.get("id")
                if not service_id:
                    continue

                try:
                    versions = app_connector.list_versions(service_id)

                    for version in versions:
                        version_id = version.get("id")
                        if not version_id:
                            continue

                        try:
                            instances = self.list_instances(
                                service_id, version_id, params
                            )

                            for instance in instances:
                                try:
                                    instance_id = instance.get("id")

                                    if not instance_id:
                                        _LOGGER.warning(
                                            f"Instance without ID found in service {service_id}, version {version_id}"
                                        )
                                        continue

                                    instance_details = self.get_instance_details(
                                        service_id, version_id, instance_id, params
                                    )
                                    if instance_details:
                                        instance.update(instance_details)

                                    metrics = self.get_instance_metrics(
                                        service_id, version_id, instance_id, params
                                    )
                                    if metrics:
                                        instance["metrics"] = metrics
                                    instance_data = {
                                        "instance_id": str(instance_id),
                                        "project_id": str(project_id),
                                        "service_id": str(service_id),
                                        "version_id": str(version_id),
                                        "vm_status": str(
                                            instance.get("vmStatus")
                                            or instance.get("status")
                                            or instance.get("servingStatus")
                                            or (
                                                instance.get("availability")
                                                if instance.get("availability")
                                                in ["RUNNING", "DYNAMIC", "RESIDENT"]
                                                else None
                                            )
                                            or "UNKNOWN"
                                        ),
                                        "vm_debug_enabled": bool(
                                            instance.get("vmDebugEnabled", False)
                                        ),
                                        "vm_liveness": str(
                                            instance.get(
                                                "vmLiveness",
                                                instance.get("liveness", ""),
                                            )
                                        ),
                                        "request_count": self._extract_request_count(
                                            instance, instance_id
                                        ),
                                        "memory_usage": self._convert_memory_usage(
                                            instance, instance_id
                                        ),
                                        "cpu_usage": float(
                                            instance.get("cpuUsage", 0) or 0
                                        ),
                                        "qps": float(instance.get("qps", 0) or 0),
                                        "average_latency": float(
                                            instance.get("averageLatency", 0) or 0
                                        ),
                                        "errors": int(instance.get("errors", 0) or 0),
                                        "create_time": convert_datetime(
                                            instance.get(
                                                "startTime", instance.get("createTime")
                                            )
                                        ),
                                        "start_time": convert_datetime(
                                            instance.get("startTime", "")
                                        ),
                                    }

                                    if "metrics" in instance:
                                        metrics_data = instance["metrics"]

                                        enhanced_metrics = {
                                            "memory_usage_enhanced": metrics_data.get(
                                                "memory_usage", ""
                                            ),
                                            "cpu_usage_enhanced": metrics_data.get(
                                                "cpu_usage", ""
                                            ),
                                            "request_count_enhanced": metrics_data.get(
                                                "request_count", ""
                                            ),
                                            "app_engine_release_enhanced": metrics_data.get(
                                                "app_engine_release", ""
                                            ),
                                        }

                                        if "memory_usage" in metrics_data:
                                            safe_metrics = {
                                                k: v
                                                for k, v in metrics_data.items()
                                                if k != "memory_usage"
                                            }
                                            instance_data.update(safe_metrics)

                                        instance_data.update(enhanced_metrics)

                                    if "vmDetails" in instance:
                                        vm_details = instance["vmDetails"]
                                        if isinstance(vm_details, dict):
                                            instance_data["vm_details"] = vm_details
                                        else:
                                            _LOGGER.warning(
                                                f"vmDetails is not a dict for instance {instance_id}: {type(vm_details)}"
                                            )

                                    if "appEngineRelease" in instance:
                                        instance_data["app_engine_release"] = str(
                                            instance["appEngineRelease"]
                                        )

                                    availability_data = None

                                    for field_name in [
                                        "availability",
                                        "vmLiveness",
                                        "liveness",
                                        "status",
                                    ]:
                                        if field_name in instance:
                                            availability_data = instance[field_name]
                                            break

                                    if availability_data is not None:
                                        if isinstance(availability_data, dict):
                                            instance_data["availability"] = (
                                                availability_data
                                            )
                                        elif isinstance(availability_data, str):
                                            instance_data["availability"] = {
                                                "liveness": availability_data,
                                                "readiness": "",
                                            }
                                        else:
                                            instance_data["availability"] = {
                                                "liveness": str(availability_data),
                                                "readiness": "",
                                            }
                                    else:
                                        vm_status = instance_data.get(
                                            "vm_status", "UNKNOWN"
                                        )
                                        liveness_status = (
                                            "HEALTHY"
                                            if vm_status == "RUNNING"
                                            else "UNHEALTHY"
                                            if vm_status != "UNKNOWN"
                                            else ""
                                        )
                                        instance_data["availability"] = {
                                            "liveness": liveness_status,
                                            "readiness": "",
                                        }

                                    if "network" in instance:
                                        network = instance["network"]
                                        if isinstance(network, dict):
                                            instance_data["network"] = network
                                        else:
                                            _LOGGER.warning(
                                                f"network is not a dict for instance {instance_id}: {type(network)}"
                                            )

                                    if "resources" in instance:
                                        resources = instance["resources"]
                                        if isinstance(resources, dict):
                                            instance_data["resources"] = resources
                                        else:
                                            _LOGGER.warning(
                                                f"resources is not a dict for instance {instance_id}: {type(resources)}"
                                            )

                                    if not instance_id:
                                        _LOGGER.warning(
                                            f"Instance missing ID, skipping monitoring setup: service={service_id}, version={version_id}"
                                        )
                                        instance_id = "unknown"

                                    instance_data["google_cloud_monitoring"] = {
                                        "name": f"projects/{project_id}",
                                        "resource_id": instance_id,
                                        "filters": [
                                            {
                                                "metric_type": "appengine.googleapis.com/http/server/response_count",
                                                "labels": [
                                                    {
                                                        "key": "resource.labels.version_id",
                                                        "value": version_id,
                                                    },
                                                ],
                                            }
                                        ],
                                    }

                                    instance_data["google_cloud_logging"] = (
                                        self.set_google_cloud_logging(
                                            "AppEngine",
                                            "Instance",
                                            project_id,
                                            instance_id,
                                        )
                                    )

                                    app_engine_instance_data = AppEngineInstance(
                                        instance_data, strict=False
                                    )

                                    instance_resource = AppEngineInstanceResource(
                                        {
                                            "name": instance_data.get("instance_id"),
                                            "data": app_engine_instance_data,
                                            "reference": {
                                                "resource_id": instance_id,
                                                "external_link": f"https://console.cloud.google.com/appengine/instances?project={project_id}&serviceId={service_id}&versionId={version_id}",
                                            },
                                            "region_code": "global",
                                            "account": instance_data.get("project_id"),
                                        }
                                    )

                                    self.set_region_code("global")

                                    instance_response = (
                                        BaseResponse.create_with_logging(
                                            state="SUCCESS",
                                            resource_type="inventory.CloudService",
                                            resource=instance_resource,
                                            match_rules={
                                                "1": [
                                                    "reference.resource_id",
                                                    "provider",
                                                    "cloud_service_type",
                                                    "cloud_service_group",
                                                ]
                                            },
                                        )
                                    )

                                    collected_cloud_services.append(instance_response)

                                except Exception as e:
                                    _LOGGER.error(
                                        f"[collect_cloud_service] Instance {instance_id} => {e}",
                                        exc_info=True,
                                    )
                                    error_response = (
                                        ErrorResourceResponse.create_with_logging(
                                            error_message=str(e),
                                            error_code="INSTANCE_COLLECTION_ERROR",
                                            resource_type="inventory.ErrorResource",
                                            additional_data={
                                                "cloud_service_group": "AppEngine",
                                                "cloud_service_type": "Instance",
                                                "resource_id": instance_id or "unknown",
                                            },
                                        )
                                    )
                                    error_responses.append(error_response)

                        except Exception as e:
                            _LOGGER.error(
                                f"[collect_cloud_service] Version {service_id}/{version_id} => {e}",
                                exc_info=True,
                            )
                            error_response = ErrorResourceResponse.create_with_logging(
                                error_message=str(e),
                                error_code="VERSION_COLLECTION_ERROR",
                                resource_type="inventory.ErrorResource",
                                additional_data={
                                    "cloud_service_group": "AppEngine",
                                    "cloud_service_type": "Instance",
                                    "resource_id": f"{service_id}/{version_id}",
                                },
                            )
                            error_responses.append(error_response)

                except Exception as e:
                    _LOGGER.error(
                        f"[collect_cloud_service] Service {service_id} => {e}",
                        exc_info=True,
                    )
                    error_response = ErrorResourceResponse.create_with_logging(
                        error_message=str(e),
                        error_code="SERVICE_COLLECTION_ERROR",
                        resource_type="inventory.ErrorResource",
                        additional_data={
                            "cloud_service_group": "AppEngine",
                            "cloud_service_type": "Instance",
                            "resource_id": service_id or "unknown",
                        },
                    )
                    error_responses.append(error_response)

        except Exception as e:
            _LOGGER.error(f"[collect_cloud_service] => {e}", exc_info=True)
            error_response = ErrorResourceResponse.create_with_logging(
                error_message=str(e),
                error_code="COLLECTION_ERROR",
                resource_type="inventory.ErrorResource",
                additional_data={
                    "cloud_service_group": "AppEngine",
                    "cloud_service_type": "Instance",
                    "resource_id": "AppEngine Instance Collection",
                },
            )
            error_responses.append(error_response)

        log_state_summary()

        _LOGGER.debug("** AppEngine Instance V1Beta END **")
        return collected_cloud_services, error_responses
