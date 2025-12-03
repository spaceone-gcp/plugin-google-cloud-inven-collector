import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["TopicConnector"]
_LOGGER = logging.getLogger(__name__)


class TopicConnector(GoogleCloudConnector):
    google_client_service = "pubsub"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_topics(self, **query):
        topics = []
        query.update({"project": self._make_project_fmt()})
        request = self.client.projects().topics().list(**query)

        while request is not None:
            response = request.execute()
            # extend 사용하여 모든 페이지 결과 누적 (= 대신 extend)
            topics.extend(response.get("topics", []))
            request = (
                self.client.projects()
                .topics()
                .list_next(previous_request=request, previous_response=response)
            )
        return topics

    def list_snapshot_names(self, topic_name):
        snapshots = []
        query = {"topic": topic_name}
        snapshot_service = self.client.projects().topics().snapshots()
        request = snapshot_service.list(**query)

        while request is not None:
            response = request.execute()
            # extend 사용하여 모든 페이지 결과 누적 (= 대신 extend)
            snapshots.extend(response.get("snapshots", []))
            request = snapshot_service.list_next(
                previous_request=request, previous_response=response
            )
        return snapshots

    def list_subscription_names(self, topic_name):
        subscriptions = []
        query = {"topic": topic_name}
        subscription_service = self.client.projects().topics().subscriptions()
        request = subscription_service.list(**query)

        while request is not None:
            response = request.execute()
            # extend 사용하여 모든 페이지 결과 누적 (= 대신 extend)
            subscriptions.extend(response.get("subscriptions", []))
            request = subscription_service.list_next(
                previous_request=request, previous_response=response
            )
        return subscriptions

    def get_subscription(self, subscription_name):
        query = {"subscription": subscription_name}
        subscription_service = self.client.projects().subscriptions()
        request = subscription_service.get(**query)
        response = request.execute()
        return response

    def get_snapshot(self, snapshot_name):
        query = {"snapshot": snapshot_name}
        snapshot_service = self.client.projects().snapshots()
        request = snapshot_service.get(**query)
        response = request.execute()
        return response

    def _make_project_fmt(self):
        return f"projects/{self.project_id}"
