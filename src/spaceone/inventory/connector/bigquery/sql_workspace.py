import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["SQLWorkspaceConnector"]
_LOGGER = logging.getLogger(__name__)


class SQLWorkspaceConnector(GoogleCloudConnector):
    google_client_service = "bigquery"
    version = "v2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_dataset(self, **query):
        dataset_list = []
        query.update({"projectId": self.project_id})
        request = self.client.datasets().list(**query)
        while request is not None:
            response = request.execute()
            for dataset in response.get("datasets", []):
                dataset_list.append(dataset)
            request = self.client.datasets().list_next(
                previous_request=request, previous_response=response
            )

        return dataset_list

    def get_dataset(self, dataset_id, **query):
        query.update({"projectId": self.project_id, "datasetId": dataset_id})
        response = {}
        response = self.client.datasets().get(**query).execute()

        return response
