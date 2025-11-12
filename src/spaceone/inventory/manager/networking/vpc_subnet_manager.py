import logging
import time
from ipaddress import IPv4Address, ip_address

from spaceone.inventory.connector.networking.vpc_subnet import VPCSubnetConnector
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import (
    ReferenceModel,
    log_state_summary,
    reset_state_counters,
)
from spaceone.inventory.model.networking.vpc_subnet.cloud_service import (
    VPCSubnetResource,
    VPCSubnetResponse,
)
from spaceone.inventory.model.networking.vpc_subnet.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.networking.vpc_subnet.data import IPAddress, VPCSubnet

_LOGGER = logging.getLogger(__name__)


class VPCSubnetManager(GoogleCloudManager):
    connector_name = "VPCSubnetConnector"
    cloud_service_types = CLOUD_SERVICE_TYPES

    def collect_cloud_service(self, params):
        _LOGGER.debug("** VPC Subnet START **")
        start_time = time.time()
        """
        Args:
            params:
                - options
                - schema
                - secret_data
                - filter
                - zones
        Response:
            CloudServiceResponse/ErrorResourceResponse
        """

        # v2.0 logging system: initialize state counters
        reset_state_counters()
        
        collected_cloud_services = []
        error_responses = []
        subnet_id = ""

        secret_data = params["secret_data"]
        project_id = secret_data["project_id"]

        ##################################
        # 0. Gather All Related Resources
        # List all information through connector
        ##################################
        subnet_conn: VPCSubnetConnector = self.locator.get_connector(
            self.connector_name, **params
        )

        # Get lists that relate with subnets through Google Cloud API
        subnets = subnet_conn.list_subnetworks()
        networks = subnet_conn.list_networks()
        regional_address = subnet_conn.list_regional_addresses()

        # Create network lookup dictionary for display names
        network_lookup = {network.get("selfLink"): network.get("name", "") for network in networks}

        for subnet in subnets:
            try:
                ##################################
                # 1. Set Basic Information
                ##################################
                subnet_id = subnet.get("id")
                network_link = subnet.get("network", "")
                network_name = network_lookup.get(network_link, "")

                # Get IP addresses for this subnet
                ip_addresses = self._get_internal_ip_addresses_in_subnet(
                    subnet, regional_address, network_name
                )

                subnet.update(
                    {
                        "project": secret_data["project_id"],
                        "network_display": network_name,
                        "region": self.get_param_in_url(subnet.get("region"), "regions"),
                        "google_access": (
                            "On" if subnet.get("privateIpGoogleAccess") else "Off"
                        ),
                        "flow_log": self._get_flow_log_status(subnet),
                        "ip_address_data": ip_addresses,
                    }
                )

                # No labels
                _name = subnet.get("name", "")

                ##################################
                # 2. Make Base Data
                ##################################
                subnet.update({
                    "google_cloud_monitoring": self.set_google_cloud_monitoring(
                        project_id, "vpc_subnet", subnet_id, [
                            {"key": "resource.labels.subnetwork_id", "value": subnet_id}
                        ]
                    ),
                    "google_cloud_logging": self.set_google_cloud_logging(
                        "Networking", "VPCSubnet", project_id, subnet_id
                    ),
                })
                subnet_data = VPCSubnet(subnet, strict=False)

                ##################################
                # 3. Make Return Resource
                ##################################
                subnet_resource = VPCSubnetResource(
                    {
                        "name": _name,
                        "account": project_id,
                        "cloud_service_group": "Networking",
                        "cloud_service_type": "VPCSubnet",
                        "region_code": subnet_data.region,
                        "data": subnet_data,
                        "reference": ReferenceModel(subnet_data.reference()),
                    }
                )

                ##################################
                # 4. Make Collected Region Code
                ##################################
                self.set_region_code(subnet_data.region)

                ##################################
                # 5. Make Resource Response Object
                # v2.0 logging system: create SUCCESS response
                ##################################
                subnet_response = VPCSubnetResponse.create_with_logging(
                    state="SUCCESS",
                    resource_type="inventory.CloudService",
                    resource=subnet_resource,
                )
                collected_cloud_services.append(subnet_response)
            except Exception as e:
                _LOGGER.error(f"[collect_cloud_service] => {e}", exc_info=True)
                error_response = self.generate_resource_error_response(
                    e, "VPC", "VPCSubnet", subnet_id
                )
                error_responses.append(error_response)

        # v2.0 logging system: log state summary when collection is complete
        log_state_summary()
        _LOGGER.debug(f"** VPC Subnet Finished {time.time() - start_time:.2f} Seconds **")
        _LOGGER.info(f"Collected {len(collected_cloud_services)} VPC Subnets")
        
        return collected_cloud_services, error_responses

    def _get_internal_ip_addresses_in_subnet(self, subnet, regional_address, network_name):
        """Retrieve the list of internal IP addresses belonging to the subnet."""
        all_internal_addresses = []
        subnet_link = subnet.get("selfLink", "")

        for ip_addr in regional_address:
            ip_type = ip_addr.get("addressType", "")
            subnetwork = ip_addr.get("subnetwork", "")

            if ip_type == "INTERNAL" and subnetwork == subnet_link:
                url_region = ip_addr.get("region")
                users = ip_addr.get("users")
                ip_addr.update(
                    {
                        "subnet_name": subnet.get("name"),
                        "ip_version_display": self._valid_ip_address(
                            ip_addr.get("address")
                        ),
                        "region": (
                            self.get_param_in_url(url_region, "regions")
                            if url_region
                            else "global"
                        ),
                        "used_by": self._get_parse_users(users) if users else ["None"],
                        "is_ephemeral": "Static",
                    }
                )

                all_internal_addresses.append(IPAddress(ip_addr, strict=False))

        return all_internal_addresses

    def _get_flow_log_status(self, subnet):
        """Check the Flow Log status of the subnet."""
        log_config = subnet.get("logConfig", {})
        return "On" if log_config.get("enable") else "Off"

    @staticmethod
    def _valid_ip_address(ip):
        """Validate IP address and return its version."""
        try:
            return "IPv4" if type(ip_address(ip)) is IPv4Address else "IPv6"
        except ValueError:
            return "Invalid"

    def _get_parse_users(self, users):
        """Parse IP address user information."""
        parsed_used_by = []
        for url_user in users:
            zone = self.get_param_in_url(url_user, "zones")
            instance = self.get_param_in_url(url_user, "instances")
            used = f"VM instance {instance} (Zone: {zone})"
            parsed_used_by.append(used)

        return parsed_used_by
