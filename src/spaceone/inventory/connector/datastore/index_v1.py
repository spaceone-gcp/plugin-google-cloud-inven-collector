import logging

from googleapiclient.errors import HttpError

from spaceone.inventory.libs.connector import GoogleCloudConnector

_LOGGER = logging.getLogger(__name__)


class DatastoreIndexV1Connector(GoogleCloudConnector):
    google_client_service = "datastore"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_indexes(self):
        try:
            # https://cloud.google.com/datastore/docs/reference/admin/rest/v1/projects.indexes/list
            request = self.client.projects().indexes().list(projectId=self.project_id)

            response = request.execute()

            indexes = response.get("indexes", [])

            return indexes

        except HttpError as e:
            if e.resp.status == 404:
                _LOGGER.warning(
                    f"Datastore service not available for project {self.project_id} "
                )
                return []
            elif e.resp.status == 403:
                _LOGGER.warning(
                    f"Datastore API not enabled or insufficient permissions for project {self.project_id}, "
                )
                return []
            else:
                _LOGGER.error(
                    f"HTTP error listing indexes for project {self.project_id}: {e}"
                )
                raise e
        except Exception as e:
            _LOGGER.error(f"Error listing indexes for project {self.project_id}: {e}")
            raise e
