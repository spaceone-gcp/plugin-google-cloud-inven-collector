import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["CloudAssetConnector"]
_LOGGER = logging.getLogger(__name__)


class CloudAssetConnector(GoogleCloudConnector):
    google_client_service = "cloudasset"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_assets_in_project(self, **query):
        total_assets = []
        query.update({"parent": f"projects/{self.project_id}"})
        request = self.client.assets().list(**query)

        while request is not None:
            response = request.execute()
            for asset in response.get("assets", {}):
                total_assets.append(asset)
            request = self.client.assets().list_next(
                previous_request=request, previous_response=response
            )
        return total_assets
