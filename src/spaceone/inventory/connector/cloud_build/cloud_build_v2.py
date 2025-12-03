import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["CloudBuildV2Connector"]
_LOGGER = logging.getLogger(__name__)


class CloudBuildV2Connector(GoogleCloudConnector):
    google_client_service = "cloudbuild"
    version = "v2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_locations(self, name, **query):
        locations = []
        query.update({"name": name})
        try:
            request = self.client.projects().locations().list(**query)
        except Exception as e:
            _LOGGER.warning(f"V2 API: Failed to create request for locations: {e}")
            return locations

        while request is not None:
            try:
                response = request.execute()
                raw_locations = response.get("locations", [])
                # Exclude global location
                filtered_locations = [
                    loc for loc in raw_locations if loc.get("locationId") != "global"
                ]
                locations.extend(filtered_locations)
                request = (
                    self.client.projects().locations().list_next(request, response)
                )
            except Exception as e:
                _LOGGER.warning(f"V2 API: Failed to list locations: {e}")
                break

        return locations

    def list_connections(self, parent, **query):
        connections = []
        query.update({"parent": parent})
        try:
            request = self.client.projects().locations().connections().list(**query)
        except Exception as e:
            _LOGGER.warning(f"V2 API: Failed to create request for connections: {e}")
            return connections

        while request is not None:
            try:
                response = request.execute()
                connections.extend(response.get("connections", []))
                request = (
                    self.client.projects()
                    .locations()
                    .connections()
                    .list_next(request, response)
                )
            except Exception as e:
                _LOGGER.warning(f"V2 API: Failed to list connections: {e}")
                break

        return connections

    def list_repositories(self, parent, **query):
        repositories = []
        query.update({"parent": parent})
        try:
            request = (
                self.client.projects()
                .locations()
                .connections()
                .repositories()
                .list(**query)
            )
        except Exception as e:
            _LOGGER.warning(f"V2 API: Failed to create request for repositories: {e}")
            return repositories

        while request is not None:
            try:
                response = request.execute()
                repositories.extend(response.get("repositories", []))
                request = (
                    self.client.projects()
                    .locations()
                    .connections()
                    .repositories()
                    .list_next(request, response)
                )
            except Exception as e:
                _LOGGER.warning(f"V2 API: Failed to list repositories: {e}")
                break

        return repositories
