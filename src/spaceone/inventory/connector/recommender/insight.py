import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["InsightConnector"]
_LOGGER = logging.getLogger(__name__)


class InsightConnector(GoogleCloudConnector):
    google_client_service = "recommender"
    version = "v1beta1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_insight(self, name):
        try:
            return (
                self.client.projects()
                .locations()
                .insightTypes()
                .insights()
                .get(name=name)
                .execute()
            )
        except Exception as e:
            _LOGGER.warning(f"Failed to get insight {name}: {e}")
            return None
