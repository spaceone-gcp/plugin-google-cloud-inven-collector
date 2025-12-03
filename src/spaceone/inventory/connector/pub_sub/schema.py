import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["SchemaConnector"]
_LOGGER = logging.getLogger(__name__)


class SchemaConnector(GoogleCloudConnector):
    google_client_service = "pubsub"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_schema_names(self, **query):
        schema_names = []
        query.update({"parent": self._make_parent()})
        request = self.client.projects().schemas().list(**query)

        while request is not None:
            response = request.execute()
            schema_names = [schema["name"] for schema in response.get("schemas", [])]
            request = (
                self.client.projects()
                .schemas()
                .list_next(previous_request=request, previous_response=response)
            )
        return schema_names

    def get_schema(self, schema_name):
        query = {"name": schema_name}
        schema_service = self.client.projects().schemas()
        request = schema_service.get(**query)
        response = request.execute()
        return response

    def _make_parent(self):
        return f"projects/{self.project_id}"
