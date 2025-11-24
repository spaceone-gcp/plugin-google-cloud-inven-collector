import logging

from spaceone.inventory.conf.kms_config import (
    COMMON_KMS_LOCATIONS,
    KMS_API_CONFIG,
    LOCATION_DISPLAY_NAMES,
    LOG_LEVEL_CONFIG,
)
from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["KMSConnector"]
_LOGGER = logging.getLogger(__name__)


class KMSConnector(GoogleCloudConnector):
    """
    Google Cloud KMS KeyRing Connector

    Class responsible for KMS KeyRing API calls
    - List KeyRings
    - Efficient location filtering support

    API version: v1
    Reference: https://cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings/list
    """

    google_client_service = "cloudkms"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def list_locations(self):
        """
        List all locations where KMS is available.

        Returns:
            list: List of all locations
        """
        try:
            request = (
                self.client.projects()
                .locations()
                .list(name=f"projects/{self.project_id}")
            )

            response = request.execute()

            locations = response.get("locations", [])
            return locations

        except Exception as e:
            _LOGGER.error(f"Error listing locations: {e}")
            raise e

    def list_key_rings(self, location):
        """
        List all KeyRings in a specific location.

        Args:
            location (str): Location to query keyrings (e.g., "global", "us-central1")

        Returns:
            list: List of all keyrings in the location
        """
        try:
            key_rings = []
            page_token = None

            while True:
                request_params = {
                    "parent": f"projects/{self.project_id}/locations/{location}",
                    "pageSize": KMS_API_CONFIG["page_size"],
                }

                if page_token:
                    request_params["pageToken"] = page_token

                request = (
                    self.client.projects().locations().keyRings().list(**request_params)
                )

                response = request.execute()

                current_key_rings = response.get("keyRings", [])
                key_rings.extend(current_key_rings)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return key_rings

        except Exception as e:
            raise e

    def list_all_key_rings(self, target_locations=None):
        """
        List KeyRings in all locations or specified locations.

        Args:
            target_locations (list, optional): Specific location ID list to search.
                                             If None, search all locations

        Returns:
            list: List of keyrings from all locations (including location info)
        """
        try:
            all_key_rings = []

            if target_locations:
                search_locations = target_locations
            else:
                location_data_list = self.list_locations()
                search_locations = [
                    loc.get("locationId", "")
                    for loc in location_data_list
                    if loc.get("locationId")
                ]

            found_locations = []
            for location_id in search_locations:
                if not location_id:
                    continue

                try:
                    key_rings = self.list_key_rings(location_id)

                    if key_rings:
                        found_locations.append(location_id)

                        location_data = self._get_location_info(location_id)

                        for key_ring in key_rings:
                            key_ring["location_id"] = location_id
                            key_ring["location_data"] = location_data
                            all_key_rings.append(key_ring)

                except Exception as e:
                    _LOGGER.warning(
                        f"Failed to list key rings in location {location_id}: {type(e).__name__}: {e}"
                    )
                    continue

            return all_key_rings

        except Exception as e:
            _LOGGER.error(f"Error listing all key rings: {e}")
            raise e

    def _get_common_locations_only(self):
        """
        Return only common locations (significantly reduced search).

        Returns:
            list: List of common location IDs only
        """
        try:
            all_locations_data = self.list_locations()
            all_location_ids = [
                loc.get("locationId", "")
                for loc in all_locations_data
                if loc.get("locationId")
            ]

            common_locations = [
                loc for loc in COMMON_KMS_LOCATIONS if loc in all_location_ids
            ]

            return common_locations

        except Exception as e:
            _LOGGER.warning(
                f"Failed to get common locations, falling back to default: {e}"
            )
            return ["global", "us-central1", "asia-northeast3"]

    def _get_optimized_location_list(self):
        """
        Return optimized location search order.
        Search common locations first, then remaining locations.

        Returns:
            list: Location ID list in optimized order
        """
        try:
            all_locations_data = self.list_locations()
            all_location_ids = [
                loc.get("locationId", "")
                for loc in all_locations_data
                if loc.get("locationId")
            ]

            priority_locations = [
                loc for loc in COMMON_KMS_LOCATIONS if loc in all_location_ids
            ]

            remaining_locations = [
                loc for loc in all_location_ids if loc not in COMMON_KMS_LOCATIONS
            ]

            optimized_order = priority_locations + remaining_locations

            return optimized_order

        except Exception as e:
            _LOGGER.warning(
                f"Failed to get optimized location list, falling back to all locations: {e}"
            )
            location_data_list = self.list_locations()
            return [
                loc.get("locationId", "")
                for loc in location_data_list
                if loc.get("locationId")
            ]

    def _get_location_info(self, location_id):
        """
        Get detailed information for a specific location.

        Args:
            location_id (str): Location ID

        Returns:
            dict: Location information
        """
        try:
            return {
                "locationId": location_id,
                "displayName": self._get_location_display_name(location_id),
                "labels": {},
            }
        except Exception as e:
            _LOGGER.warning(f"Failed to get location info for {location_id}: {e}")
            return {"locationId": location_id, "displayName": location_id, "labels": {}}

    def _get_location_display_name(self, location_id):
        """
        Convert Location ID to user-friendly name.

        Args:
            location_id (str): Location ID

        Returns:
            str: Display name
        """
        return LOCATION_DISPLAY_NAMES.get(location_id, location_id)

    def list_crypto_keys(self, keyring_name):
        """
        List all CryptoKeys in a specific KeyRing.

        Args:
            keyring_name (str): Full name of the KeyRing (e.g., "projects/test/locations/global/keyRings/my-keyring")

        Returns:
            list: List of all CryptoKeys in the KeyRing
        """
        try:
            crypto_keys = []
            page_token = None

            while True:
                request_params = {
                    "parent": keyring_name,
                    "pageSize": KMS_API_CONFIG["page_size"],
                }

                if page_token:
                    request_params["pageToken"] = page_token

                request = (
                    self.client.projects()
                    .locations()
                    .keyRings()
                    .cryptoKeys()
                    .list(**request_params)
                )

                response = request.execute()

                current_crypto_keys = response.get("cryptoKeys", [])
                crypto_keys.extend(current_crypto_keys)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return crypto_keys

        except Exception as e:
            log_level = LOG_LEVEL_CONFIG.get("crypto_key_not_found", "INFO")
            if log_level == "INFO":
                _LOGGER.info(f"No crypto keys found in keyring {keyring_name}: {e}")
            elif log_level == "WARNING":
                _LOGGER.warning(
                    f"Error listing crypto keys in keyring {keyring_name}: {e}"
                )
            else:
                _LOGGER.error(
                    f"Error listing crypto keys in keyring {keyring_name}: {e}"
                )
            return []

    def list_crypto_key_versions(self, crypto_key_name):
        """
        List all CryptoKeyVersions for a specific CryptoKey.

        Args:
            crypto_key_name (str): Full name of the CryptoKey
                                 (e.g., "projects/test/locations/global/keyRings/my-keyring/cryptoKeys/my-key")

        Returns:
            list: List of all CryptoKeyVersions for the CryptoKey
        """
        try:
            crypto_key_versions = []
            page_token = None

            while True:
                request_params = {
                    "parent": crypto_key_name,
                    "pageSize": KMS_API_CONFIG["page_size"],
                    "view": "FULL",
                }

                if page_token:
                    request_params["pageToken"] = page_token

                request = (
                    self.client.projects()
                    .locations()
                    .keyRings()
                    .cryptoKeys()
                    .cryptoKeyVersions()
                    .list(**request_params)
                )

                response = request.execute()

                current_versions = response.get("cryptoKeyVersions", [])
                crypto_key_versions.extend(current_versions)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return crypto_key_versions

        except Exception as e:
            log_level = LOG_LEVEL_CONFIG.get("crypto_key_not_found", "INFO")
            if log_level == "INFO":
                _LOGGER.info(
                    f"No crypto key versions found in crypto key {crypto_key_name}: {e}"
                )
            elif log_level == "WARNING":
                _LOGGER.warning(
                    f"Error listing crypto key versions in crypto key {crypto_key_name}: {e}"
                )
            else:
                _LOGGER.error(
                    f"Error listing crypto key versions in crypto key {crypto_key_name}: {e}"
                )
            return []
