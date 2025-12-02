import logging
import re
import time
from typing import Dict, List, Tuple

from spaceone.inventory.connector.batch.batch_v1 import BatchV1Connector
from spaceone.inventory.libs.batch_processor import BatchJobProcessor
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import (
    ReferenceModel,
    log_state_summary,
    reset_state_counters,
)
from spaceone.inventory.libs.schema.cloud_service import (
    CloudServiceResponse,
    ErrorResourceResponse,
)
from spaceone.inventory.model.batch.job.cloud_service import (
    JobResource,
    JobResponse,
)
from spaceone.inventory.model.batch.job.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.batch.job.data import BatchJobResource

_LOGGER = logging.getLogger(__name__)


class BatchManager(GoogleCloudManager):
    """Batch Manager that manages individual Jobs as resources"""

    connector_name = "BatchV1Connector"
    cloud_service_types = CLOUD_SERVICE_TYPES

    def collect_cloud_service(self, params) -> Tuple[List[CloudServiceResponse], List]:
        """
        Collect Batch Jobs as individual resources.

        Args:
            params: Collection parameters (secret_data, options, schema, filter)

        Returns:
            Tuple[List[CloudServiceResponse], List]: (collected Job resources, error responses)
        """
        start_time = time.time()

        reset_state_counters()

        collected_cloud_services = []
        error_responses = []

        try:
            project_id = params["secret_data"]["project_id"]
            batch_connector = self._get_connector(params)

            all_jobs = batch_connector.list_all_jobs()
            if not all_jobs:
                return collected_cloud_services, error_responses

            for job in all_jobs:
                try:
                    job_resource = self._create_job_resource(
                        job, project_id, batch_connector, params
                    )
                    collected_cloud_services.append(job_resource)

                except Exception as e:
                    job_name = job.get("name", "unknown")
                    _LOGGER.error(
                        f"Failed to process job {job_name}: {e}", exc_info=True
                    )

                    error_response = ErrorResourceResponse.create_with_logging(
                        error=e,
                        provider="google_cloud",
                        cloud_service_group="Batch",
                        cloud_service_type="Job",
                        resource_id=job_name,
                    )
                    error_responses.append(error_response)

        except Exception as e:
            _LOGGER.error(f"Batch Job collection failed: {e}", exc_info=True)
            error_response = ErrorResourceResponse.create_with_logging(
                error=e,
                provider="google_cloud",
                cloud_service_group="Batch",
                cloud_service_type="Job",
                resource_id="batch-service",
            )
            error_responses.append(error_response)

        log_state_summary()
        _LOGGER.info(
            f"Collected {len(collected_cloud_services)} Batch Jobs in {time.time() - start_time:.2f}s"
        )
        return collected_cloud_services, error_responses

    def _get_connector(self, params) -> BatchV1Connector:
        """Get connector instance."""
        return self.locator.get_connector(self.connector_name, **params)

    def _parse_job_name(self, job_name: str) -> Tuple[str, str, str]:
        """
        Extract project, location, and job_id from job name.

        Args:
            job_name: Full path name of the job

        Returns:
            Tuple[str, str, str]: (project_id, location_id, job_id)
        """
        try:
            job_pattern = r"projects/([^/]+)/locations/([^/]+)/jobs/([^/]+)"
            match = re.match(job_pattern, job_name)

            if match:
                return match.group(1), match.group(2), match.group(3)

        except Exception as e:
            _LOGGER.warning(f"Error parsing job name {job_name}: {e}")

        _LOGGER.warning(f"Could not parse job name: {job_name}")
        return "unknown", "unknown", job_name

    def _create_job_resource(
        self,
        job: Dict,
        project_id: str,
        batch_connector: BatchV1Connector,
        params: Dict,
    ) -> CloudServiceResponse:
        """
        Create individual Job resource.

        Args:
            job: Job data
            project_id: Project ID
            batch_connector: Batch connector
            params: Collection parameters

        Returns:
            CloudServiceResponse: Created Job resource response
        """
        try:
            job_name = job.get("name", "")
            _, location_id, job_id = self._parse_job_name(job_name)

            job_processor = BatchJobProcessor(batch_connector)
            processed_jobs = job_processor.process_jobs([job])

            if not processed_jobs:
                raise ValueError(f"Failed to process job data for {job_name}")

            processed_job = processed_jobs[0]

            task_count = 0
            all_tasks = []
            task_groups = processed_job.get("task_groups", [])
            for task_group in task_groups:
                group_task_count = task_group.get("task_count", "0")
                try:
                    task_count += int(group_task_count)
                except (ValueError, TypeError):
                    _LOGGER.warning(f"Invalid task_count value: {group_task_count}")

                tasks = task_group.get("tasks", [])
                all_tasks.extend(tasks)

            display_name = processed_job.get("display_name", "")
            if not display_name:
                display_name = job_id

            google_cloud_monitoring_filters = [
                {"key": "resource.labels.job_id", "value": job_id},
            ]

            job_data = BatchJobResource(
                {
                    "name": job_name,
                    "uid": processed_job.get("uid"),
                    "display_name": display_name,
                    "state": processed_job.get("state"),
                    "create_time": processed_job.get("create_time"),
                    "update_time": processed_job.get("update_time"),
                    "location_id": location_id,
                    "project_id": project_id,
                    "task_groups": task_groups,
                    "task_count": task_count,
                    "all_tasks": all_tasks,
                    "labels": job.get("labels", {}),
                    "annotations": job.get("annotations", {}),
                    "google_cloud_monitoring": self._set_multiple_google_cloud_monitoring(
                        project_id,
                        [
                            "logging.googleapis.com/byte_count",
                            "logging.googleapis.com/log_entry_count",
                        ],
                        job_id,
                        google_cloud_monitoring_filters,
                    ),
                    "google_cloud_logging": self.set_google_cloud_logging(
                        "Batch", "Job", project_id, job_id
                    ),
                }
            )

            resource = JobResource(
                {
                    "name": job_id,
                    "account": project_id,
                    "data": job_data,
                    "reference": ReferenceModel(job_data.reference()),
                    "region_code": location_id,
                }
            )

            return JobResponse({"resource": resource})

        except Exception as e:
            _LOGGER.error(
                f"Failed to create Batch job resource for {job.get('name', 'unknown')}: {e}",
                exc_info=True,
            )
            raise e

    @staticmethod
    def _set_multiple_google_cloud_monitoring(
        project_id, metric_types, resource_id, filters
    ):
        """
        Set multiple Google Cloud Monitoring metric types for Batch Job.

        Args:
            project_id (str): GCP project ID
            metric_types (list): List of metric types
            resource_id (str): Resource ID
            filters (list): Filters to apply to all metric types

        Returns:
            dict: Google Cloud Monitoring configuration with multiple metric types
        """
        monitoring_filters = []
        for metric_type in metric_types:
            monitoring_filters.append({"metric_type": metric_type, "labels": filters})

        return {
            "name": f"projects/{project_id}",
            "resource_id": resource_id,
            "filters": monitoring_filters,
        }
