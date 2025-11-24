import logging

import googleapiclient

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["FirebaseConnector"]
_LOGGER = logging.getLogger(__name__)


class FirebaseConnector(GoogleCloudConnector):
    google_client_service = "firebase"
    version = "v1beta1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.secret_data = kwargs.get("secret_data", {})

        firebase_scopes = [
            "https://www.googleapis.com/auth/firebase",
            "https://www.googleapis.com/auth/firebase.readonly",
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/cloud-platform.read-only",
        ]

        if hasattr(self, "credentials") and hasattr(self.credentials, "with_scopes"):
            self.credentials = self.credentials.with_scopes(firebase_scopes)
            self.client = googleapiclient.discovery.build(
                self.google_client_service, self.version, credentials=self.credentials
            )

    def list_firebase_apps(self, **query):
        """
        List Firebase apps for a specific project.
        Uses the searchApps endpoint of Firebase Management API.

        Args:
            **query: Additional query parameters

        Returns:
            list: List of Firebase apps
        """
        try:
            parent = f"projects/{self.project_id}"
            query.update({"parent": parent})

            apps = []
            request = self.client.projects().searchApps(**query)

            while request is not None:
                response = request.execute()
                for app in response.get("apps", []):
                    apps.append(app)
                request = self.client.projects().searchApps_next(
                    previous_request=request, previous_response=response
                )

            return apps

        except Exception as e:
            _LOGGER.error(
                f"Failed to list Firebase apps for project {self.project_id}: {e}"
            )
            raise e

    def get_firebase_project_info(self, **query):
        """
        List Firebase apps and check service usage.

        Args:
            **query: Additional query parameters

        Returns:
            dict: Firebase app list and service usage status
        """
        try:
            firebase_apps = self.list_firebase_apps()

            return {
                "firebaseApps": firebase_apps,
                "hasFirebaseServices": len(firebase_apps) > 0,
            }

        except Exception as e:
            _LOGGER.error(f"Failed to get Firebase apps for {self.project_id}: {e}")
            raise e

    def get_app_details(self, app_name):
        """
        Get detailed information for a specific Firebase app.

        Args:
            app_name (str): Firebase app name (format: projects/{project}/iosApps/{app-id})

        Returns:
            dict: App details
        """
        try:
            if "/iosApps/" in app_name:
                response = self.client.projects().iosApps().get(name=app_name).execute()
            elif "/androidApps/" in app_name:
                response = (
                    self.client.projects().androidApps().get(name=app_name).execute()
                )
            elif "/webApps/" in app_name:
                response = self.client.projects().webApps().get(name=app_name).execute()
            else:
                return {}

            return response
        except Exception as e:
            _LOGGER.warning(f"Failed to get app details for {app_name}: {e}")
            return {}

    def get_project(self, project_id):
        """
        Get detailed information for a specific Firebase project.

        Args:
            project_id (str): Firebase project ID

        Returns:
            dict: Project details
        """
        try:
            response = (
                self.client.projects().get(name=f"projects/{project_id}").execute()
            )
            return response
        except Exception as e:
            _LOGGER.error(f"Failed to get Firebase project {project_id}: {e}")
            raise e

    def get_analytics_details(self, project_id):
        """
        Get Google Analytics connection information for Firebase project.

        Args:
            project_id (str): Firebase project ID

        Returns:
            dict: Analytics connection information (if available)
        """
        try:
            response = (
                self.client.projects().get(name=f"projects/{project_id}").execute()
            )

            analytics_paths = [
                "analyticsProperty",
                "googleAnalyticsProperty",
                "resources.analyticsProperty",
                "resources.googleAnalyticsProperty",
            ]

            for path in analytics_paths:
                current_data = response
                keys = path.split(".")

                try:
                    for key in keys:
                        current_data = current_data.get(key, {})

                    if current_data and isinstance(current_data, str):
                        return {"analyticsProperty": current_data}

                except (AttributeError, TypeError):
                    continue

            return {}

        except Exception as e:
            _LOGGER.warning(f"Failed to get Analytics details for {project_id}: {e}")
            return {}

    def list_available_resources(self, project_id):
        """
        List all available resource types for Firebase project.

        Args:
            project_id (str): Firebase project ID

        Returns:
            dict: Available resource information
        """
        try:
            project_info = self.get_project(project_id)

            available_resources = {
                "project_info": project_info,
                "analytics_details": self.get_analytics_details(project_id),
            }

            return available_resources

        except Exception as e:
            _LOGGER.error(f"Failed to list available resources for {project_id}: {e}")
            return {}
