import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["CloudRunV1Connector"]

_LOGGER = logging.getLogger(__name__)


class CloudRunV1Connector(GoogleCloudConnector):
    google_client_service = "run"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def list_locations(self, name, **query):
        """Query locations from V1 API"""
        locations = []
        query.update({"name": name})
        _LOGGER.info(f"V1 API: Getting locations for name: {name}")

        try:
            request = self.client.projects().locations().list(**query)
        except Exception as e:
            _LOGGER.warning(f"V1 API: Failed to create request for locations: {e}")
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
                _LOGGER.warning(f"V1 API: Failed to list locations: {e}")
                break

        return locations

    def list_domain_mappings(self, parent, **query):
        domain_mappings = []
        query.update({"parent": parent})

        while True:
            try:
                response = (
                    self.client.namespaces().domainmappings().list(**query).execute()
                )
                domain_mappings.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list domain mappings: {e}")
                break

        return domain_mappings

    def list_services(self, parent, **query):
        """Query services from V1 API (namespace-based)"""
        services = []
        query.update({"parent": parent})

        while True:
            try:
                response = self.client.namespaces().services().list(**query).execute()
                services.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list services: {e}")
                break

        return services

    def list_jobs(self, parent, **query):
        """Query jobs from V1 API (limited support, namespace-based)"""
        jobs = []
        query.update({"parent": parent})

        while True:
            try:
                response = self.client.namespaces().jobs().list(**query).execute()
                jobs.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list jobs: {e}")
                break

        return jobs

    def list_revisions(self, parent, **query):
        """Query revisions from V1 API (namespace-based)"""
        revisions = []
        query.update({"parent": parent})

        while True:
            try:
                response = self.client.namespaces().revisions().list(**query).execute()
                revisions.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list revisions: {e}")
                break

        return revisions

    def list_executions(self, parent, **query):
        """Query executions from V1 API (namespace-based)"""
        executions = []
        query.update({"parent": parent})

        while True:
            try:
                response = self.client.namespaces().executions().list(**query).execute()
                executions.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list executions: {e}")
                break

        return executions

    def list_tasks(self, parent, **query):
        """Query tasks from V1 API (namespace-based)"""
        tasks = []
        query.update({"parent": parent})

        while True:
            try:
                response = self.client.namespaces().tasks().list(**query).execute()
                tasks.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list tasks: {e}")
                break

        return tasks

    def list_routes(self, parent, **query):
        """Query routes from V1 API (namespace-based)"""
        routes = []
        query.update({"parent": parent})

        while True:
            try:
                response = self.client.namespaces().routes().list(**query).execute()
                routes.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list routes: {e}")
                break

        return routes

    def list_configurations(self, parent, **query):
        """Query configurations from V1 API (namespace-based)"""
        configurations = []
        query.update({"parent": parent})

        while True:
            try:
                response = (
                    self.client.namespaces().configurations().list(**query).execute()
                )
                configurations.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list configurations: {e}")
                break

        return configurations

    def list_worker_pools(self, parent, **query):
        """Query worker pools from V1 API (namespace-based)"""
        worker_pools = []
        query.update({"parent": parent})

        while True:
            try:
                response = (
                    self.client.namespaces().workerpools().list(**query).execute()
                )
                worker_pools.extend(response.get("items", []))

                continue_token = response.get("metadata", {}).get("continue")
                if continue_token:
                    query["continue"] = continue_token
                else:
                    break
            except Exception as e:
                _LOGGER.warning(f"Failed to list worker pools: {e}")
                break

        return worker_pools
