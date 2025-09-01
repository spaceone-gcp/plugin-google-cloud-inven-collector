import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from spaceone.inventory.connector.cloud_build.cloud_build_v2 import (
    CloudBuildV2Connector,
)
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import ReferenceModel
from spaceone.inventory.model.cloud_build.worker_pool.cloud_service import (
    WorkerPoolResource,
    WorkerPoolResponse,
)
from spaceone.inventory.model.cloud_build.worker_pool.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.cloud_build.worker_pool.data import WorkerPool

_LOGGER = logging.getLogger(__name__)


class CloudBuildWorkerPoolManager(GoogleCloudManager):
    connector_name = "CloudBuildV1Connector"
    cloud_service_types = CLOUD_SERVICE_TYPES

    def collect_cloud_service(self, params):
        _LOGGER.debug("** Cloud Build WorkerPool START **")
        start_time = time.time()
        """
        Args:
            params:
                - options
                - schema
                - secret_data
                - filter
                - zones
        Response:
            CloudServiceResponse/ErrorResourceResponse
        """

        collected_cloud_services = []
        error_responses = []
        worker_pool_id = ""

        secret_data = params["secret_data"]
        project_id = secret_data["project_id"]

        ##################################
        # 0. Gather All Related Resources
        # List all information through connector
        ##################################

        cloud_build_v2_conn: CloudBuildV2Connector = self.locator.get_connector(
            "CloudBuildV2Connector", **params
        )

        # Get lists that relate with worker pools through Google Cloud API with parallel processing
        all_worker_pools = []
        try:
            parent = f"projects/{project_id}"
            locations = cloud_build_v2_conn.list_locations(parent)

            # 병렬 처리 최적화: 14개 워커 (11.3% 성능 향상, 효율적 처리)
            max_workers = min(14, len(locations))

            _LOGGER.info(
                f"🔧 Starting parallel Cloud Build worker pool processing: "
                f"locations={len(locations)}, max_workers={max_workers}"
            )

            def _get_location_worker_pools(location):
                """위치별 워커 풀 수집 (스레드 안전)"""
                location_id = location.get("locationId", "")
                if not location_id:
                    return []

                try:
                    # 스레드별 독립적인 커넥터 사용
                    thread_conn = self.locator.get_connector(
                        self.connector_name, **params
                    )
                    parent = f"projects/{project_id}/locations/{location_id}"
                    worker_pools = thread_conn.list_location_worker_pools(parent)

                    for worker_pool in worker_pools:
                        worker_pool["_location"] = location_id

                    _LOGGER.debug(
                        f"✅ Location {location_id}: {len(worker_pools)} worker pools"
                    )
                    return worker_pools

                except Exception as e:
                    _LOGGER.debug(
                        f"❌ Failed to query worker pools in location {location_id}: {str(e)}"
                    )
                    return []

            # 병렬 처리 실행
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_location = {
                    executor.submit(_get_location_worker_pools, location): location
                    for location in locations
                }

                for future in as_completed(future_to_location, timeout=60):
                    location = future_to_location[future]
                    try:
                        location_worker_pools = future.result(timeout=20)
                        all_worker_pools.extend(location_worker_pools)
                    except Exception as e:
                        location_id = location.get("locationId", "unknown")
                        _LOGGER.debug(
                            f"❌ Location {location_id} worker pool processing failed: {str(e)}"
                        )

        except Exception as e:
            _LOGGER.warning(f"Failed to get locations: {str(e)}")

        _LOGGER.info(
            f"cloud worker pool all_worker_pools length: {len(all_worker_pools)}"
        )
        for worker_pool in all_worker_pools:
            try:
                ##################################
                # 1. Set Basic Information
                ##################################
                worker_pool_id = worker_pool.get("name", "")
                worker_pool_name = (
                    self.get_param_in_url(worker_pool_id, "workerPools")
                    if worker_pool_id
                    else ""
                )
                location_id = worker_pool.get("_location", "")
                region = self.parse_region_from_zone(location_id) if location_id else ""

                ##################################
                # 2. Make Base Data
                ##################################
                worker_pool.update(
                    {
                        "project": project_id,
                        "location": location_id,
                        "region": region,
                    }
                )

                ##################################
                # 3. Make Return Resource
                ##################################
                worker_pool_data = WorkerPool(worker_pool, strict=False)

                worker_pool_resource = WorkerPoolResource(
                    {
                        "name": worker_pool_name,
                        "account": project_id,
                        "region_code": location_id,
                        "data": worker_pool_data,
                        "reference": ReferenceModel(
                            {
                                "resource_id": worker_pool_data.name,
                                "external_link": f"https://console.cloud.google.com/cloud-build/worker-pools?project={project_id}",
                            }
                        ),
                    },
                    strict=False,
                )

                collected_cloud_services.append(
                    WorkerPoolResponse({"resource": worker_pool_resource})
                )

            except Exception as e:
                _LOGGER.error(
                    f"Failed to process worker pool {worker_pool_id}: {str(e)}"
                )
                error_response = self.generate_resource_error_response(
                    e, "CloudBuild", "WorkerPool", worker_pool_id
                )
                error_responses.append(error_response)

        _LOGGER.debug(
            f"** Cloud Build WorkerPool END ** ({time.time() - start_time:.2f}s)"
        )

        return collected_cloud_services, error_responses
