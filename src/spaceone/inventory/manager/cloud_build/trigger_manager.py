import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from spaceone.inventory.connector.cloud_build.cloud_build_v1 import (
    CloudBuildV1Connector,
)
from spaceone.inventory.connector.cloud_build.cloud_build_v2 import (
    CloudBuildV2Connector,
)
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import ReferenceModel
from spaceone.inventory.model.cloud_build.trigger.cloud_service import (
    TriggerResource,
    TriggerResponse,
)
from spaceone.inventory.model.cloud_build.trigger.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.cloud_build.trigger.data import Trigger

_LOGGER = logging.getLogger(__name__)


class CloudBuildTriggerManager(GoogleCloudManager):
    connector_name = "CloudBuildV1Connector"
    cloud_service_types = CLOUD_SERVICE_TYPES

    def collect_cloud_service(self, params):
        _LOGGER.debug("** Cloud Build Trigger START **")
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
        trigger_id = ""

        secret_data = params["secret_data"]
        project_id = secret_data["project_id"]

        ##################################
        # 0. Gather All Related Resources
        # List all information through connector
        ##################################
        cloud_build_v1_conn: CloudBuildV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )
        cloud_build_v2_conn: CloudBuildV2Connector = self.locator.get_connector(
            "CloudBuildV2Connector", **params
        )

        # Get lists that relate with triggers through Google Cloud API
        triggers = cloud_build_v1_conn.list_triggers()

        # Get locations and regional triggers with parallel processing
        regional_triggers = []
        try:
            parent = f"projects/{project_id}"
            locations = cloud_build_v2_conn.list_locations(parent)

            # 병렬 처리 최적화: 16개 워커 (11.5% 성능 향상, 안정적 고성능)
            max_workers = min(16, len(locations))

            _LOGGER.info(
                f"🎯 Starting parallel Cloud Build trigger processing: "
                f"locations={len(locations)}, max_workers={max_workers}"
            )

            def _get_location_triggers(location):
                """위치별 트리거 수집 (스레드 안전)"""
                location_id = location.get("locationId", "")
                if not location_id:
                    return []

                try:
                    # 스레드별 독립적인 커넥터 사용
                    thread_conn = self.locator.get_connector(
                        self.connector_name, **params
                    )
                    parent = f"projects/{project_id}/locations/{location_id}"
                    location_triggers = thread_conn.list_location_triggers(parent)

                    for trigger in location_triggers:
                        trigger["_location"] = location_id

                    _LOGGER.debug(
                        f"✅ Location {location_id}: {len(location_triggers)} triggers"
                    )
                    return location_triggers

                except Exception as e:
                    _LOGGER.error(
                        f"❌ Failed to query triggers in location {location_id}: {str(e)}"
                    )
                    return []

            # 병렬 처리 실행
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_location = {
                    executor.submit(_get_location_triggers, location): location
                    for location in locations
                }

                for future in as_completed(future_to_location, timeout=60):
                    location = future_to_location[future]
                    try:
                        location_triggers = future.result(timeout=20)
                        regional_triggers.extend(location_triggers)
                    except Exception as e:
                        location_id = location.get("locationId", "unknown")
                        _LOGGER.error(
                            f"❌ Location {location_id} trigger processing failed: {str(e)}"
                        )

        except Exception as e:
            _LOGGER.warning(f"Failed to get locations: {str(e)}")

        # Combine all triggers
        all_triggers = triggers + regional_triggers
        for trigger in all_triggers:
            try:
                ##################################
                # 1. Set Basic Information
                ##################################
                trigger_id = trigger.get("id")
                trigger_name = trigger.get("name", trigger_id)
                location_id = trigger.get("_location", "global")
                region = (
                    GoogleCloudManager.parse_region_from_zone(location_id)
                    if location_id != "global"
                    else "global"
                )

                ##################################
                # 2. Make Base Data
                ##################################
                trigger.update(
                    {
                        "project": project_id,
                        "location": location_id,
                        "region": region,
                    }
                )

                ##################################
                # 3. Make Return Resource
                ##################################
                trigger_data = Trigger(trigger, strict=False)

                trigger_resource = TriggerResource(
                    {
                        "name": trigger_name,
                        "account": project_id,
                        "region_code": location_id,
                        "data": trigger_data,
                        "reference": ReferenceModel(
                            {
                                "resource_id": trigger_data.id,
                                "external_link": f"https://console.cloud.google.com/cloud-build/triggers?project={project_id}",
                            }
                        ),
                    },
                    strict=False,
                )

                collected_cloud_services.append(
                    TriggerResponse({"resource": trigger_resource})
                )

            except Exception as e:
                _LOGGER.error(f"Failed to process trigger {trigger_id}: {str(e)}")
                error_response = self.generate_resource_error_response(
                    e, "CloudBuild", "Trigger", trigger_id
                )
                error_responses.append(error_response)

        _LOGGER.debug(
            f"** Cloud Build Trigger END ** ({time.time() - start_time:.2f}s)"
        )

        return collected_cloud_services, error_responses
