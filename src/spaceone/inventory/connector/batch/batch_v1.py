import logging
from typing import Dict, List

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["BatchV1Connector"]

_LOGGER = logging.getLogger(__name__)


class BatchV1Connector(GoogleCloudConnector):
    """Optimized Batch Connector with efficient API calls and error handling"""

    google_client_service = "batch"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_all_jobs(self, **query) -> List[Dict]:
        """
        List all Batch Jobs.

        Args:
            **query: Additional query parameters

        Returns:
            List[Dict]: List of all Jobs
        """
        parent = f"projects/{self.project_id}/locations/-"
        return self._paginated_list(
            self.client.projects().locations().jobs().list,
            parent=parent,
            resource_key="jobs",
            error_context="list all jobs",
            **query,
        )

    def list_tasks(self, task_group_name: str, **query) -> List[Dict]:
        """
        List tasks in a TaskGroup.

        Args:
            task_group_name: Full path of the TaskGroup
            **query: Additional query parameters

        Returns:
            List[Dict]: List of tasks
        """
        return self._paginated_list(
            self.client.projects().locations().jobs().taskGroups().tasks().list,
            parent=task_group_name,
            resource_key="tasks",
            error_context=f"list tasks for {task_group_name}",
            **query,
        )

    def _paginated_list(
        self, api_method, resource_key: str, error_context: str, **query
    ) -> List[Dict]:
        """
        Common pagination handling logic for API calls.

        Args:
            api_method: API method (e.g., client.jobs().list)
            resource_key: Resource key to extract from response (e.g., 'jobs', 'tasks')
            error_context: Context for error logging
            **query: API query parameters

        Returns:
            List[Dict]: Collected resource list
        """
        resources = []

        try:
            request = api_method(**query)
            while request is not None:
                response = request.execute()

                page_resources = response.get(resource_key, [])
                resources.extend(page_resources)

                request = self._get_next_request(api_method, request, response)

        except Exception as e:
            _LOGGER.warning(f"Failed to {error_context}: {e}")

        return resources

    def _get_next_request(self, api_method, request, response):
        """
        Generate next page request (optimized pagination handling).

        Args:
            api_method: Original API method
            request: Current request
            response: Current response

        Returns:
            Next page request or None
        """
        try:
            method_path = str(api_method)

            next_method_mapping = {
                "tasks().list": lambda: self.client.projects()
                .locations()
                .jobs()
                .taskGroups()
                .tasks()
                .list_next,
                "jobs().list": lambda: self.client.projects()
                .locations()
                .jobs()
                .list_next,
            }

            for pattern, next_method_getter in next_method_mapping.items():
                if pattern in method_path:
                    next_method = next_method_getter()
                    return next_method(
                        previous_request=request, previous_response=response
                    )

            return (
                self.client.projects()
                .locations()
                .list_next(previous_request=request, previous_response=response)
            )

        except (AttributeError, Exception) as e:
            _LOGGER.debug(f"No more pages available or error in pagination: {e}")
            return None

    def get_job_details(self, name: str, **query) -> Dict:
        """
        Get detailed information for a specific Job (optional use only).

        Args:
            name: Full path name of the job
            **query: Additional query parameters

        Returns:
            Dict: Job details
        """
        query.update({"name": name})
        try:
            return self.client.projects().locations().jobs().get(**query).execute()
        except Exception as e:
            _LOGGER.warning(f"Failed to get job details {name}: {e}")
            return {}

    def get_task_details(self, name: str, **query) -> Dict:
        """
        Get detailed information for a specific Task (optional use only).

        Args:
            name: Full path name of the task
            **query: Additional query parameters

        Returns:
            Dict: Task details
        """
        query.update({"name": name})
        try:
            return (
                self.client.projects()
                .locations()
                .jobs()
                .taskGroups()
                .tasks()
                .get(**query)
                .execute()
            )
        except Exception as e:
            _LOGGER.warning(f"Failed to get task details {name}: {e}")
            return {}
