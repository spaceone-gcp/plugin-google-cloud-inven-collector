import logging
from typing import Any, Dict, List, Tuple

from spaceone.inventory.connector.app_engine.application_v1 import (
    AppEngineApplicationV1Connector,
)
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.cloud_service import ErrorResourceResponse
from spaceone.inventory.model.app_engine.application.cloud_service import (
    AppEngineApplicationResource,
    AppEngineApplicationResponse,
)
from spaceone.inventory.model.app_engine.application.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.app_engine.application.data import AppEngineApplication

_LOGGER = logging.getLogger(__name__)


class AppEngineApplicationV1Manager(GoogleCloudManager):
    connector_name = "AppEngineApplicationV1Connector"
    cloud_service_types = CLOUD_SERVICE_TYPES
    cloud_service_group = "AppEngine"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_application(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get App Engine application information (v1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            App Engine application information dictionary.

        Raises:
            Exception: When App Engine API call fails.
        """
        app_connector: AppEngineApplicationV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            application = app_connector.get_application()
            if application:
                _LOGGER.info("Retrieved AppEngine application (v1)")
            return application or {}
        except Exception as e:
            _LOGGER.error(f"Failed to get AppEngine application (v1): {e}")
            return {}

    def list_services(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List App Engine services (v1 API).

        Args:
            params: Parameters dictionary for query.

        Returns:
            List of App Engine services.

        Raises:
            Exception: When App Engine API call fails.
        """
        app_connector: AppEngineApplicationV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            services = app_connector.list_services()
            _LOGGER.info(f"Found {len(services)} AppEngine services (v1)")
            return services
        except Exception as e:
            _LOGGER.error(f"Failed to list AppEngine services (v1): {e}")
            return []

    def list_versions(
        self, service_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """List versions for a specific service (v1 API).

        Args:
            service_id: Service ID.
            params: Parameters dictionary for query.

        Returns:
            List of service versions.

        Raises:
            Exception: When App Engine API call fails.
        """
        app_connector: AppEngineApplicationV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            versions = app_connector.list_versions(service_id)
            _LOGGER.info(
                f"Found {len(versions)} versions for service {service_id} (v1)"
            )
            return versions
        except Exception as e:
            _LOGGER.error(f"Failed to list versions for service {service_id} (v1): {e}")
            return []

    def list_instances(
        self, service_id: str, version_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """List instances for a specific version (v1 API).

        Args:
            service_id: Service ID.
            version_id: Version ID.
            params: Parameters dictionary for query.

        Returns:
            List of instances.

        Raises:
            Exception: When App Engine API call fails.
        """
        app_connector: AppEngineApplicationV1Connector = self.locator.get_connector(
            self.connector_name, **params
        )

        try:
            instances = app_connector.list_instances(service_id, version_id)
            _LOGGER.info(
                f"Found {len(instances)} instances for version {version_id} (v1)"
            )
            return instances
        except Exception as e:
            _LOGGER.error(
                f"Failed to list instances for version {version_id} (v1): {e}"
            )
            return []

    def collect_cloud_service(
        self, params: Dict[str, Any]
    ) -> Tuple[List[Any], List[ErrorResourceResponse]]:
        """Collect App Engine application information (v1 API).

        Args:
            params: Parameters dictionary for collection.

        Returns:
            Tuple of collected cloud service list and error response list.

        Raises:
            Exception: When data collection fails.
        """
        _LOGGER.debug("** AppEngine Application V1 START **")

        collected_cloud_services = []
        error_responses = []

        secret_data = params["secret_data"]
        project_id = secret_data["project_id"]

        application = self.get_application(params)

        if application:
            try:
                services = self.list_services(params)

                # 버전 및 인스턴스 정보 수집
                total_versions = 0
                total_instances = 0

                for service in services:
                    service_id = service.get("id")
                    if service_id:
                        versions = self.list_versions(service_id, params)
                        total_versions += len(versions)

                        for version in versions:
                            version_id = version.get("id")
                            if version_id:
                                instances = self.list_instances(
                                    service_id, version_id, params
                                )
                                total_instances += len(instances)

                # 기본 애플리케이션 데이터 준비
                app_data = {
                    "name": str(application.get("name", "")),
                    "projectId": str(
                        project_id
                    ),  # secret_data에서 가져온 project_id 사용
                    "locationId": str(application.get("locationId", "")),
                    "servingStatus": str(application.get("servingStatus", "")),
                    "defaultHostname": str(application.get("defaultHostname", "")),
                    "codeBucket": str(application.get("codeBucket", "")),
                    "gcrDomain": str(application.get("gcrDomain", "")),
                    "databaseType": str(application.get("databaseType", "")),
                    # 실제 API에서 제공하는 추가 필드들
                    "authDomain": str(application.get("authDomain", "")),
                    "defaultBucket": str(application.get("defaultBucket", "")),
                    "serviceAccount": str(application.get("serviceAccount", "")),
                    "sslPolicy": str(application.get("sslPolicy", "")),
                    "version_count": str(total_versions),
                    "instance_count": str(total_instances),
                }

                # Feature Settings 추가
                if "featureSettings" in application:
                    feature_settings = application["featureSettings"]
                    app_data["featureSettings"] = {
                        "splitHealthChecks": str(
                            feature_settings.get("splitHealthChecks", "")
                        ),
                        "useContainerOptimizedOs": str(
                            feature_settings.get("useContainerOptimizedOs", "")
                        ),
                    }

                # IAP Settings 추가
                if "iap" in application:
                    iap_settings = application["iap"]
                    app_data["iap"] = {
                        "enabled": str(iap_settings.get("enabled", "")),
                        "oauth2ClientId": str(iap_settings.get("oauth2ClientId", "")),
                        "oauth2ClientSecret": str(
                            iap_settings.get("oauth2ClientSecret", "")
                        ),
                    }

                # URL Dispatch Rules 추가
                if "dispatchRules" in application:
                    dispatch_rules = application["dispatchRules"]
                    app_data["dispatchRules"] = []
                    for rule in dispatch_rules:
                        app_data["dispatchRules"].append(
                            {
                                "domain": str(rule.get("domain", "")),
                                "path": str(rule.get("path", "")),
                                "service": str(rule.get("service", "")),
                            }
                        )

                # Stackdriver 정보 추가
                app_id = application.get("id", "default")
                # Google Cloud Monitoring/Logging 리소스 ID: App Engine의 경우 module_id (app_id) 사용
                monitoring_resource_id = app_id

                google_cloud_monitoring_filters = [
                    {"key": "resource.labels.project_id", "value": project_id},
                ]
                app_data["google_cloud_monitoring"] = self.set_google_cloud_monitoring(
                    project_id,
                    "appengine.googleapis.com/system",
                    monitoring_resource_id,
                    google_cloud_monitoring_filters,
                )
                app_data["google_cloud_logging"] = self.set_google_cloud_logging(
                    "AppEngine", "Application", project_id, monitoring_resource_id
                )

                # AppEngineApplication 모델 생성
                app_engine_app_data = AppEngineApplication(app_data, strict=False)

                # AppEngineApplicationResource 생성
                app_resource = AppEngineApplicationResource(
                    {
                        "name": app_data.get("name"),
                        "data": app_engine_app_data,
                        "reference": {
                            "resource_id": application.get("name"),
                            "external_link": f"https://console.cloud.google.com/appengine?project={project_id}",
                        },
                        "region_code": app_data.get("locationId"),
                        "account": app_data.get("projectId"),
                    }
                )

                ##################################
                # 4. Make Collected Region Code
                ##################################
                self.set_region_code(app_data.get("locationId"))

                # AppEngineApplicationResponse 생성
                app_response = AppEngineApplicationResponse({"resource": app_resource})

                collected_cloud_services.append(app_response)

            except Exception as e:
                _LOGGER.error(f"[collect_cloud_service] => {e}", exc_info=True)
                error_responses.append(
                    self.generate_error_response(
                        e, self.cloud_service_group, "Application"
                    )
                )

        _LOGGER.debug("** AppEngine Application V1 END **")
        return collected_cloud_services, error_responses
