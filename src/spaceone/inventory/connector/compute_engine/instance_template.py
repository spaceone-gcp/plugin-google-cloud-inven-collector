import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["InstanceTemplateConnector"]
_LOGGER = logging.getLogger(__name__)


class InstanceTemplateConnector(GoogleCloudConnector):
    google_client_service = "compute"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_instance_templates(self, **query):
        instance_template_list = []
        query.update({"project": self.project_id})
        request = self.client.instanceTemplates().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, _instance_template_list in response["items"].items():
                if "instanceTemplates" in _instance_template_list:
                    instance_template_list.extend(
                        _instance_template_list.get("instanceTemplates")
                    )
            request = self.client.instanceTemplates().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return instance_template_list

    def list_instance_group_managers(self, **query):
        instance_group_manager_list = []
        query.update({"project": self.project_id})
        request = self.client.instanceGroupManagers().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, _instance_group_manager_list in response["items"].items():
                if "instanceGroupManagers" in _instance_group_manager_list:
                    instance_group_manager_list.extend(
                        _instance_group_manager_list.get("instanceGroupManagers")
                    )
            request = self.client.instanceGroupManagers().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return instance_group_manager_list
