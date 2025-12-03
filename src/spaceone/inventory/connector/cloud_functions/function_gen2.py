import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["FunctionGen2Connector"]
_LOGGER = logging.getLogger(__name__)


class FunctionGen2Connector(GoogleCloudConnector):
    google_client_service = "cloudfunctions"
    version = "v2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_functions(self):
        functions = []
        query = {"parent": self._make_parent()}
        functions_service = self.client.projects().locations().functions()
        request = functions_service.list(**query)

        while request is not None:
            response = request.execute()
            functions = response.get("functions", [])
            request = functions_service.list_next(
                previous_request=request, previous_response=response
            )
        return functions

    def _make_parent(self):
        return f"projects/{self.project_id}/locations/-"
