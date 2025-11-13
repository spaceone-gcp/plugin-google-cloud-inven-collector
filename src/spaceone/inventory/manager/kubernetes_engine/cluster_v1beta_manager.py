import logging
import re
from typing import Any, Dict, List, Tuple

from spaceone.inventory.connector.kubernetes_engine.cluster_v1beta import (
    GKEClusterV1BetaConnector,
)
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.cloud_service import ErrorResourceResponse
from spaceone.inventory.model.kubernetes_engine.cluster.cloud_service import (
    GKEClusterResource,
    GKEClusterResponse,
)
from spaceone.inventory.model.kubernetes_engine.cluster.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.kubernetes_engine.cluster.data import (
    GKECluster,
    convert_datetime,
)

_LOGGER = logging.getLogger(__name__)


class GKEClusterV1BetaManager(GoogleCloudManager):
    connector_name = "GKEClusterV1BetaConnector"
    cloud_service_types = CLOUD_SERVICE_TYPES
    cloud_service_group = "KubernetesEngine"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def list_clusters(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List GKE clusters (v1beta1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of GKE clusters.

        Raises:
            Exception: When GKE API call fails.
        """
        cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            clusters = cluster_connector.list_clusters()
            _LOGGER.info(f"Found {len(clusters)} GKE clusters (v1beta1)")
            return clusters
        except Exception as e:
            _LOGGER.error(f"Failed to list GKE clusters (v1beta1): {e}")
            return []

    # NodePool 관련 기능은 별도의 NodePoolManager에서 처리
    # def list_node_pools(self, cluster_name: str, location: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    #     """특정 클러스터의 노드풀 목록을 조회합니다 (v1beta1 API).
    #
    #     이 메서드는 제거되었습니다. 노드풀 정보는 GKENodePoolManager를 사용하세요.
    #     """
    #     _LOGGER.warning("list_node_pools method is deprecated. Use GKENodePoolManager instead.")
    #     return []

    def get_cluster(
        self, name: str, location: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get specific GKE cluster information (v1beta1 API).

        Args:
            name: Cluster name.
            location: Cluster location.
            params: Parameters dictionary for query.

        Returns:
            GKE cluster information dictionary.

        Raises:
            Exception: When GKE API call fails.
        """
        cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            cluster = cluster_connector.get_cluster(name, location)
            if cluster:
                _LOGGER.info(f"Retrieved cluster {name} (v1beta1)")
            return cluster or {}
        except Exception as e:
            _LOGGER.error(f"Failed to get cluster {name} (v1beta1): {e}")
            return {}

    def list_operations(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List GKE operations (v1beta1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of GKE operations.

        Raises:
            Exception: When GKE API call fails.
        """
        cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            operations = cluster_connector.list_operations()
            _LOGGER.info(f"Found {len(operations)} GKE operations (v1beta1)")
            return operations
        except Exception as e:
            _LOGGER.error(f"Failed to list GKE operations (v1beta1): {e}")
            return []

    def get_resource_limits(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get GKE resource limits information.

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of GKE resource limits.

        Raises:
            Exception: When GKE API call fails.
        """
        try:
            cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
                self.connector_name, **params
            )

            # Container Engine 관련 할당량 조회
            resource_limits = cluster_connector.get_container_engine_quotas()
            _LOGGER.info(f"Found {len(resource_limits)} GKE resource limits")
            return resource_limits
        except Exception as e:
            _LOGGER.error(f"Failed to get GKE resource limits: {e}")
            return []

    def calculate_cluster_resources(
        self, cluster_name: str, location: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate total CPU and memory for a cluster by aggregating node pool information.

        Args:
            cluster_name: Cluster name
            location: Cluster location
            params: Query parameters

        Returns:
            Dictionary containing total CPU and memory information
        """
        try:
            from spaceone.inventory.connector.kubernetes_engine.cluster_v1beta import (
                GKEClusterV1BetaConnector,
            )

            cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
                self.connector_name, **params
            )

            node_pools = cluster_connector.list_node_pools(cluster_name, location)

            if not node_pools:
                return {
                    "total_nodes": 0,
                    "machine_type": "Unknown",
                }

            total_cpu = 0
            total_memory_gb = 0
            total_nodes = 0

            # Machine type to CPU/Memory mapping (common GCP machine types)
            machine_type_specs = {
                # E2 machine types
                "e2-micro": {"cpu": 1, "memory_gb": 1},
                "e2-small": {"cpu": 1, "memory_gb": 2},
                "e2-medium": {"cpu": 1, "memory_gb": 4},
                "e2-standard-2": {"cpu": 2, "memory_gb": 8},
                "e2-standard-4": {"cpu": 4, "memory_gb": 16},
                "e2-standard-8": {"cpu": 8, "memory_gb": 32},
                "e2-standard-16": {"cpu": 16, "memory_gb": 64},
                "e2-standard-32": {"cpu": 32, "memory_gb": 128},
                # N1 Standard machine types
                "n1-standard-1": {"cpu": 1, "memory_gb": 3.75},
                "n1-standard-2": {"cpu": 2, "memory_gb": 7.5},
                "n1-standard-4": {"cpu": 4, "memory_gb": 15},
                "n1-standard-8": {"cpu": 8, "memory_gb": 30},
                "n1-standard-16": {"cpu": 16, "memory_gb": 60},
                "n1-standard-32": {"cpu": 32, "memory_gb": 120},
                "n1-standard-64": {"cpu": 64, "memory_gb": 240},
                "n1-standard-96": {"cpu": 96, "memory_gb": 360},
                # High-memory machine types
                "n1-highmem-2": {"cpu": 2, "memory_gb": 13},
                "n1-highmem-4": {"cpu": 4, "memory_gb": 26},
                "n1-highmem-8": {"cpu": 8, "memory_gb": 52},
                "n1-highmem-16": {"cpu": 16, "memory_gb": 104},
                "n1-highmem-32": {"cpu": 32, "memory_gb": 208},
                "n1-highmem-64": {"cpu": 64, "memory_gb": 416},
                "n1-highmem-96": {"cpu": 96, "memory_gb": 624},
                # High-CPU machine types
                "n1-highcpu-16": {"cpu": 16, "memory_gb": 14.4},
                "n1-highcpu-32": {"cpu": 32, "memory_gb": 28.8},
                "n1-highcpu-64": {"cpu": 64, "memory_gb": 57.6},
                "n1-highcpu-96": {"cpu": 96, "memory_gb": 86.4},
                # N2 machine types
                "n2-standard-2": {"cpu": 2, "memory_gb": 8},
                "n2-standard-4": {"cpu": 4, "memory_gb": 16},
                "n2-standard-8": {"cpu": 8, "memory_gb": 32},
                "n2-standard-16": {"cpu": 16, "memory_gb": 64},
                "n2-standard-32": {"cpu": 32, "memory_gb": 128},
                "n2-standard-48": {"cpu": 48, "memory_gb": 192},
                "n2-standard-64": {"cpu": 64, "memory_gb": 256},
                "n2-standard-80": {"cpu": 80, "memory_gb": 320},
                "n2-standard-128": {"cpu": 128, "memory_gb": 512},
            }

            for node_pool in node_pools:
                try:
                    pool_name = node_pool.get("name", "unknown")

                    current_node_count = (
                        node_pool.get("currentNodeCount", 0)
                        or node_pool.get("initialNodeCount", 0)
                        or node_pool.get("nodeCount", 0)
                        or 0
                    )

                    if not current_node_count:
                        continue

                    total_nodes += current_node_count

                    node_config = node_pool.get("config", {})
                    machine_type = node_config.get("machineType", "")

                    if machine_type in machine_type_specs:
                        specs = machine_type_specs[machine_type]
                        pool_cpu = specs["cpu"] * current_node_count
                        pool_memory = specs["memory_gb"] * current_node_count
                        total_cpu += pool_cpu
                        total_memory_gb += pool_memory
                    else:
                        try:
                            if "-" in machine_type:
                                parts = machine_type.split("-")
                                if len(parts) >= 3 and parts[-1].isdigit():
                                    cpu_count = int(parts[-1])
                                    if "highmem" in machine_type:
                                        memory_gb = cpu_count * 6.5
                                    elif "highcpu" in machine_type:
                                        memory_gb = cpu_count * 0.9
                                    else:
                                        memory_gb = cpu_count * 3.75

                                    pool_cpu = cpu_count * current_node_count
                                    pool_memory = memory_gb * current_node_count
                                    total_cpu += pool_cpu
                                    total_memory_gb += pool_memory
                        except Exception:
                            pass

                except Exception as e:
                    _LOGGER.debug(
                        f"Error processing node pool {node_pool.get('name', 'unknown')}: {e}"
                    )
                    continue

            first_machine_type = "Unknown"
            if node_pools:
                first_node_pool = node_pools[0]
                node_config = first_node_pool.get("config", {})
                first_machine_type = node_config.get("machineType", "Unknown")

            result = {
                "total_nodes": total_nodes,
                "machine_type": first_machine_type,
            }

            return result

        except Exception as e:
            _LOGGER.debug(
                f"Failed to calculate cluster resources for {cluster_name}: {e}"
            )
            return {
                "total_nodes": 0,
                "machine_type": "Unknown",
            }

    def list_fleets(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List GKE fleets (v1beta1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of GKE fleets.

        Raises:
            Exception: When GKE API call fails.
        """
        cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            fleets = cluster_connector.list_fleets()
            _LOGGER.info(f"Found {len(fleets)} GKE fleets (v1beta1)")
            return fleets
        except Exception as e:
            _LOGGER.error(f"Failed to list GKE fleets (v1beta1): {e}")
            return []

    def list_memberships(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List GKE memberships (v1beta1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of GKE memberships.

        Raises:
            Exception: When GKE API call fails.
        """
        cluster_connector: GKEClusterV1BetaConnector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            memberships = cluster_connector.list_memberships()
            _LOGGER.info(f"Found {len(memberships)} GKE memberships (v1beta1)")
            return memberships
        except Exception as e:
            _LOGGER.error(f"Failed to list GKE memberships (v1beta1): {e}")
            return []

    def collect_cloud_service(
        self, params: Dict[str, Any]
    ) -> Tuple[List[Any], List[ErrorResourceResponse]]:
        """Collect GKE cluster information (v1beta1 API).

        Args:
            params: Parameters dictionary for collection.

        Returns:
            Tuple of collected cloud service list and error response list.

        Raises:
            Exception: When data collection fails.
        """
        _LOGGER.debug("** GKE Cluster V1Beta START **")

        collected_cloud_services = []
        error_responses = []

        secret_data = params["secret_data"]
        project_id = secret_data["project_id"]

        # GKE 클러스터 목록 조회
        clusters = self.list_clusters(params)

        # GKE 리소스 제한 정보 조회
        resource_limits = self.get_resource_limits(params)

        for cluster in clusters:
            try:
                # 클러스터별 노드풀 정보 조회
                # NodePool 정보는 별도의 NodePoolManager에서 처리

                # v1beta1 전용 정보 조회
                fleet_info = None
                membership_info = None

                # Fleet 정보 조회 (v1beta1에서만 가능)
                if cluster.get("name") and cluster.get("location"):
                    try:
                        fleets = self.list_fleets(params)
                        if fleets:
                            fleet_info = fleets[0]  # 첫 번째 fleet 정보 사용
                    except Exception as e:
                        _LOGGER.debug(f"Failed to get fleet info: {e}")

                # Membership 정보 조회 (v1beta1에서만 가능)
                if cluster.get("name") and cluster.get("location"):
                    try:
                        memberships = self.list_memberships(params)
                        if memberships:
                            membership_info = memberships[
                                0
                            ]  # 첫 번째 membership 정보 사용
                    except Exception as e:
                        _LOGGER.debug(f"Failed to get membership info: {e}")

                # Calculate total cluster resources
                cluster_name = cluster.get("name", "")
                cluster_location = cluster.get("location", "")
                cluster_resources = self.calculate_cluster_resources(
                    cluster_name, cluster_location, params
                )

                # 기본 클러스터 데이터 준비
                cluster_data = {
                    "name": str(cluster.get("name", "")),
                    "description": str(cluster.get("description", "")),
                    "location": str(cluster.get("location", "")),
                    "projectId": str(
                        project_id
                    ),  # secret_data에서 가져온 project_id 사용
                    "status": str(cluster.get("status", "")),
                    "currentMasterVersion": str(
                        cluster.get("currentMasterVersion", "")
                    ),
                    "currentNodeVersion": str(cluster.get("currentNodeVersion", "")),
                    "currentNodeCount": str(cluster.get("currentNodeCount", "")),
                    "createTime": convert_datetime(cluster.get("createTime")),
                    "resourceLabels": {
                        k: str(v) for k, v in cluster.get("resourceLabels", {}).items()
                    },
                    # Add machine type from first node pool
                    "machine_type": cluster_resources.get("machine_type", "Unknown"),
                }

                if "networkConfig" in cluster:
                    try:
                        network_config = cluster["networkConfig"]
                        if not isinstance(network_config, dict):
                            _LOGGER.warning(
                                f"Cluster {cluster_name}: networkConfig is not a dict, type: {type(network_config)}"
                            )
                            network_config = {}
                        default_snat_status = network_config.get(
                            "defaultSnatStatus", {}
                        )
                        dns_config = network_config.get("dnsConfig", {})
                        service_external_ips_config = network_config.get(
                            "serviceExternalIpsConfig", {}
                        )

                        processed_network_config = {
                            "network": str(network_config.get("network", "") or ""),
                            "subnetwork": str(
                                network_config.get("subnetwork", "") or ""
                            ),
                            # 항상 포함되는 필드들
                            # 딕셔너리 타입 필드들은 그대로 전달 (모델에서 DictType으로 정의됨)
                            "defaultSnatStatus": (
                                default_snat_status
                                if isinstance(default_snat_status, dict)
                                else {}
                            ),
                            "datapathProvider": str(
                                network_config.get("datapathProvider", "") or ""
                            ),
                            "dnsConfig": (
                                dns_config if isinstance(dns_config, dict) else {}
                            ),
                            "serviceExternalIpsConfig": (
                                service_external_ips_config
                                if isinstance(service_external_ips_config, dict)
                                else {}
                            ),
                            # 불린 타입 필드들은 그대로 유지 (모델에서 BooleanType으로 정의됨)
                            "enableFqdnNetworkPolicy": bool(
                                network_config.get("enableFqdnNetworkPolicy", False)
                            ),
                            "defaultEnablePrivateNodes": bool(
                                network_config.get("defaultEnablePrivateNodes", False)
                            ),
                            "disableL4LbFirewallReconciliation": bool(
                                network_config.get(
                                    "disableL4LbFirewallReconciliation", False
                                )
                            ),
                        }

                        # 레거시 필드들 (API 응답에 있을 때만 추가)
                        # 불린 타입 필드들은 그대로 유지 (모델에서 BooleanType으로 정의됨)
                        if "enableIntraNodeVisibility" in network_config:
                            processed_network_config["enableIntraNodeVisibility"] = (
                                bool(
                                    network_config.get(
                                        "enableIntraNodeVisibility", False
                                    )
                                )
                            )

                        if "enableL4ilbSubsetting" in network_config:
                            processed_network_config["enableL4ilbSubsetting"] = bool(
                                network_config.get("enableL4ilbSubsetting", False)
                            )

                        cluster_data.update(
                            {
                                "networkConfig": processed_network_config,
                                "network": str(network_config.get("network", "") or ""),
                                "subnetwork": str(
                                    network_config.get("subnetwork", "") or ""
                                ),
                            }
                        )
                    except Exception as e:
                        _LOGGER.error(
                            f"Cluster {cluster_name}: Failed to process networkConfig: {e}",
                            exc_info=True,
                        )
                        cluster_data.update(
                            {
                                "networkConfig": {},
                                "network": str(cluster.get("network", "") or ""),
                                "subnetwork": str(cluster.get("subnetwork", "") or ""),
                            }
                        )

                # 클러스터 IP 설정 추가
                if "clusterIpv4Cidr" in cluster:
                    cluster_data["clusterIpv4Cidr"] = str(cluster["clusterIpv4Cidr"])
                if "servicesIpv4Cidr" in cluster:
                    cluster_data["servicesIpv4Cidr"] = str(cluster["servicesIpv4Cidr"])

                # 마스터 인증 추가
                if "masterAuth" in cluster:
                    master_auth = cluster["masterAuth"]
                    cluster_data["masterAuth"] = {
                        "username": str(master_auth.get("username", "")),
                        "password": str(master_auth.get("password", "")),
                        "clusterCaCertificate": str(
                            master_auth.get("clusterCaCertificate", "")
                        ),
                    }

                if "workloadPolicyConfig" in cluster:
                    workload_policy = cluster["workloadPolicyConfig"]
                    cluster_data["workloadPolicyConfig"] = {
                        "allowNetAdmin": str(workload_policy.get("allowNetAdmin", "")),
                    }

                if "resourceUsageExportConfig" in cluster:
                    export_config = cluster["resourceUsageExportConfig"]
                    cluster_data["resourceUsageExportConfig"] = {
                        "enableNetworkEgressMetering": str(
                            export_config.get("enableNetworkEgressMetering", "")
                        ),
                    }

                if "authenticatorGroupsConfig" in cluster:
                    auth_config = cluster["authenticatorGroupsConfig"]
                    cluster_data["authenticatorGroupsConfig"] = {
                        "securityGroup": str(auth_config.get("securityGroup", "")),
                    }

                if "monitoringConfig" in cluster:
                    monitoring_config = cluster["monitoringConfig"]
                    cluster_data["monitoringConfig"] = {
                        "monitoringService": str(
                            monitoring_config.get("monitoringService", "")
                        ),
                        "loggingService": str(
                            monitoring_config.get("loggingService", "")
                        ),
                    }

                if "addonsConfig" in cluster:
                    addons_config = cluster["addonsConfig"]

                    def camel_to_snake(name):
                        """Convert camelCase to snake_case"""
                        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
                        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

                    processed_addons = {}
                    for addon_key, addon_value in addons_config.items():
                        snake_key = camel_to_snake(addon_key)
                        if isinstance(addon_value, dict):
                            processed_addons[snake_key] = addon_value
                        else:
                            processed_addons[snake_key] = str(addon_value)

                    cluster_data["addonsConfig"] = processed_addons

                if resource_limits:
                    cluster_data["resourceLimits"] = resource_limits
                if fleet_info:
                    cluster_data["fleet_info"] = {
                        "fleetProject": str(fleet_info.get("fleetProject", "")),
                        "membership": str(fleet_info.get("membership", "")),
                    }
                if membership_info:
                    cluster_data["membership_info"] = {
                        "name": str(membership_info.get("name", "")),
                        "description": str(membership_info.get("description", "")),
                        "state": str(membership_info.get("state", {})),
                    }

                cluster_name = cluster.get("name")
                cluster_location = cluster.get("location")

                if not cluster_name:
                    _LOGGER.warning(
                        f"Cluster missing name, skipping monitoring setup: {cluster}"
                    )
                    cluster_name = "unknown"

                monitoring_resource_id = (
                    f"{project_id}:{cluster_location or 'unknown'}:{cluster_name}"
                )

                google_cloud_monitoring_filters = [
                    {"key": "resource.labels.cluster_name", "value": cluster_name},
                    {
                        "key": "resource.labels.location",
                        "value": cluster_location or "unknown",
                    },
                ]
                cluster_data["google_cloud_monitoring"] = (
                    self.set_google_cloud_monitoring(
                        project_id,
                        "kubernetes.io/container",
                        monitoring_resource_id,
                        google_cloud_monitoring_filters,
                    )
                )
                cluster_data["google_cloud_logging"] = self.set_google_cloud_logging(
                    "KubernetesEngine", "Cluster", project_id, monitoring_resource_id
                )

                gke_cluster_data = GKECluster(cluster_data, strict=False)

                tags = self.convert_labels_format(cluster.get("resourceLabels", {}))

                cluster_resource = GKEClusterResource(
                    {
                        "name": cluster_data.get("name"),
                        "data": gke_cluster_data,
                        "reference": {
                            "resource_id": cluster.get("selfLink"),
                            "external_link": f"https://console.cloud.google.com/kubernetes/clusters/details/{cluster.get('location')}/{cluster.get('name')}?project={project_id}",
                        },
                        "region_code": cluster.get("location"),
                        "account": project_id,
                        "tags": tags,
                    }
                )

                self.set_region_code(cluster.get("location"))

                cluster_response = GKEClusterResponse({"resource": cluster_resource})

                collected_cloud_services.append(cluster_response)

            except Exception as e:
                _LOGGER.error(f"[collect_cloud_service] => {e}", exc_info=True)
                error_responses.append(
                    ErrorResourceResponse(
                        {
                            "message": str(e),
                            "resource": {
                                "cloud_service_group": self.cloud_service_group,
                                "cloud_service_type": "Cluster",
                            },
                        }
                    )
                )

        _LOGGER.debug("** GKE Cluster V1Beta END **")
        return collected_cloud_services, error_responses
