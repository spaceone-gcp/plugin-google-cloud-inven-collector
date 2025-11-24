import logging
import re
from typing import Dict, List, Optional, Tuple

from spaceone.inventory.connector.kms.kms_v1 import KMSConnector
from spaceone.inventory.libs.manager import GoogleCloudManager
from spaceone.inventory.libs.schema.base import (
    ReferenceModel,
    log_state_summary,
    reset_state_counters,
)
from spaceone.inventory.libs.schema.cloud_service import CloudServiceResponse
from spaceone.inventory.model.kms.keyring.cloud_service import (
    KMSKeyRingResource,
    KMSKeyRingResponse,
)
from spaceone.inventory.model.kms.keyring.cloud_service_type import (
    CLOUD_SERVICE_TYPES,
)
from spaceone.inventory.model.kms.keyring.data import KMSKeyRingData

__all__ = ["KMSKeyRingManager"]
_LOGGER = logging.getLogger(__name__)


class KMSKeyRingManager(GoogleCloudManager):
    """
    Google Cloud KMS KeyRing Manager

    Manager class for efficiently collecting and processing KMS KeyRing resources
    - Collect KeyRing list
    - Process KeyRing details
    - Generate resource responses
    """

    connector_name = "KMSConnector"
    cloud_service_types = CLOUD_SERVICE_TYPES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cloud_service_group = "KMS"
        self.cloud_service_type = "KeyRing"

    def collect_cloud_service(self, params) -> Tuple[List[CloudServiceResponse], List]:
        """
        Efficiently collect KMS KeyRing resources.

        Args:
            params (dict): Collection parameters
                - secret_data: Authentication information
                - options: Option settings

        Returns:
            Tuple[List[CloudServiceResponse], List[ErrorResourceResponse]]:
                List of successful resource responses and error responses
        """
        reset_state_counters()

        resource_responses = []
        error_responses = []

        try:
            kms_connector = self._get_connector(params)

            key_rings = self._list_key_rings(kms_connector, params)

            if not key_rings:
                from spaceone.inventory.conf.kms_config import LOG_LEVEL_CONFIG

                log_level = LOG_LEVEL_CONFIG["keyring_not_found"]
                log_method = getattr(_LOGGER, log_level.lower())
                log_method("No KeyRings found in any location")
                return resource_responses, error_responses

            for keyring_data in key_rings:
                try:
                    resource_response = self._create_keyring_response(
                        keyring_data, params
                    )
                    resource_responses.append(resource_response)
                except Exception as e:
                    keyring_name = keyring_data.get("name", "unknown")
                    _LOGGER.error(
                        f"Failed to process KeyRing {keyring_name}: {e}", exc_info=True
                    )
                    error_response = self.generate_resource_error_response(
                        e, "KMS", "KeyRing", keyring_name
                    )
                    error_responses.append(error_response)

        except Exception as e:
            _LOGGER.error(f"Failed to collect KMS KeyRings: {e}", exc_info=True)
            error_response = self.generate_resource_error_response(
                e, "KMS", "Service", "kms"
            )
            error_responses.append(error_response)

        log_state_summary()
        _LOGGER.info(f"Collected {len(resource_responses)} KMS KeyRings")
        return resource_responses, error_responses

    def _get_connector(self, params) -> KMSConnector:
        """Get connector instance."""
        return self.locator.get_connector(self.connector_name, **params)

    def _list_key_rings(
        self, kms_connector: KMSConnector, params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        List all KeyRings in KMS.

        Performance optimizations:
        - Removed nested CryptoKey queries (handle separately via API if needed)
        - Use memory-efficient data structures

        Args:
            kms_connector: KMS connector instance
            params: Collection parameters (including option settings)

        Returns:
            List[dict]: List of KeyRing information
        """
        try:
            options = params.get("options", {}) if params else {}
            specified_locations = options.get("kms_locations", None)

            if specified_locations:
                _LOGGER.info(f"Using specified KMS locations: {specified_locations}")

            raw_key_rings = kms_connector.list_all_key_rings(
                target_locations=specified_locations
            )

            processed_key_rings = []
            for key_ring in raw_key_rings:
                keyring_data = self._process_keyring_data(key_ring, kms_connector)
                if keyring_data:
                    processed_key_rings.append(keyring_data)

            return processed_key_rings

        except Exception as e:
            _LOGGER.error(f"Error listing key rings: {e}", exc_info=True)
            raise e

    def _process_keyring_data(
        self, keyring: Dict, kms_connector: KMSConnector
    ) -> Optional[Dict]:
        """
        Process KeyRing data.

        Args:
            keyring: Original KeyRing data
            kms_connector: KMS connector instance

        Returns:
            dict: Processed KeyRing data
        """
        try:
            name = keyring.get("name", "")
            create_time = keyring.get("createTime", "")
            location_id = keyring.get("location_id", "")
            location_data = keyring.get("location_data", {})

            keyring_pattern = r"projects/([^/]+)/locations/([^/]+)/keyRings/([^/]+)"
            match = re.match(keyring_pattern, name)

            if match:
                project_id = match.group(1)
                parsed_location_id = match.group(2)
                keyring_id = match.group(3)

                if not location_id:
                    location_id = parsed_location_id
            else:
                _LOGGER.warning(f"Invalid KeyRing name format: {name}")
                return None

            from spaceone.inventory.conf.kms_config import LOCATION_DISPLAY_NAMES

            location_display_name = LOCATION_DISPLAY_NAMES.get(
                location_id, location_data.get("displayName", location_id)
            )

            crypto_keys = self.get_crypto_keys_for_keyring(name, kms_connector)

            return {
                "name": name,
                "keyring_id": keyring_id,
                "project_id": project_id,
                "location_id": location_id,
                "location_display_name": location_display_name,
                "create_time": create_time,
                "display_name": keyring_id,
                "full_location_path": f"projects/{project_id}/locations/{location_id}",
                "crypto_keys": crypto_keys,
                "crypto_key_count": len(crypto_keys),
                "google_cloud_logging": self.set_google_cloud_logging(
                    "KMS", "KeyRing", project_id, keyring_id
                ),
            }

        except Exception as e:
            _LOGGER.error(f"Error processing KeyRing data: {e}", exc_info=True)
            return None

    def _create_keyring_response(
        self, keyring_data: Dict, params: Dict
    ) -> CloudServiceResponse:
        """
        Generate resource response based on KeyRing data.

        Args:
            keyring_data: KeyRing data
            params: Collection parameters

        Returns:
            CloudServiceResponse: KeyRing resource response
        """
        try:
            keyring_id = keyring_data["keyring_id"]
            project_id = keyring_data["project_id"]
            location_id = keyring_data["location_id"]

            resource_id = f"{project_id}:{location_id}:{keyring_id}"

            keyring_data_obj = KMSKeyRingData(keyring_data, strict=False)

            resource = KMSKeyRingResource(
                {
                    "name": keyring_data["display_name"],
                    "account": project_id,
                    "data": keyring_data_obj,
                    "region_code": location_id,
                    "reference": ReferenceModel(
                        {
                            "resource_id": resource_id,
                            "external_link": f"https://console.cloud.google.com/security/kms/keyring/manage/{location_id}/{keyring_id}?project={project_id}",
                        }
                    ),
                }
            )

            return KMSKeyRingResponse({"resource": resource})

        except Exception as e:
            keyring_name = keyring_data.get("name", "unknown")
            _LOGGER.error(
                f"Failed to create KMS KeyRing response for {keyring_name}: {e}",
                exc_info=True,
            )
            raise e

    def get_crypto_keys_for_keyring(
        self, keyring_name: str, kms_connector: KMSConnector
    ) -> List[Dict]:
        """
        Get basic CryptoKey information for a specific KeyRing.

        Args:
            keyring_name: Full name of the KeyRing
            kms_connector: KMS connector instance

        Returns:
            list: List of basic CryptoKey information
        """
        try:
            crypto_keys = kms_connector.list_crypto_keys(keyring_name)
            processed_crypto_keys = []

            for crypto_key in crypto_keys:
                processed_key = self._process_crypto_key_data(crypto_key, kms_connector)
                if processed_key:
                    processed_crypto_keys.append(processed_key)

            return processed_crypto_keys

        except Exception as e:
            _LOGGER.warning(f"Error collecting crypto keys for {keyring_name}: {e}")
            return []

    def _process_crypto_key_data(
        self, crypto_key: Dict, kms_connector: KMSConnector
    ) -> Optional[Dict]:
        """
        Process CryptoKey data along with CryptoKeyVersion information.

        Args:
            crypto_key: Original CryptoKey data
            kms_connector: KMS connector instance

        Returns:
            dict: Processed CryptoKey data (including CryptoKeyVersion)
        """
        try:
            name = crypto_key.get("name", "")
            purpose = crypto_key.get("purpose", "")
            create_time = crypto_key.get("createTime", "")

            crypto_key_pattern = r"projects/([^/]+)/locations/([^/]+)/keyRings/([^/]+)/cryptoKeys/([^/]+)"
            match = re.match(crypto_key_pattern, name)

            if match:
                crypto_key_id = match.group(4)
            else:
                _LOGGER.warning(f"Invalid CryptoKey name format: {name}")
                return None

            primary = crypto_key.get("primary", {})
            primary_state = primary.get("state", "")
            primary_name = primary.get("name", "")

            version_template = crypto_key.get("versionTemplate", {})
            protection_level = version_template.get("protectionLevel", "")
            algorithm = version_template.get("algorithm", "")

            next_rotation_time = crypto_key.get("nextRotationTime", "")

            crypto_key_versions = self._get_crypto_key_versions(name, kms_connector)

            return {
                "name": name,
                "crypto_key_id": crypto_key_id,
                "purpose": purpose,
                "create_time": create_time,
                "next_rotation_time": next_rotation_time,
                "primary_state": primary_state,
                "primary_name": primary_name,
                "protection_level": protection_level,
                "algorithm": algorithm,
                "display_name": f"{crypto_key_id} ({purpose})",
                "crypto_key_versions": crypto_key_versions,
                "crypto_key_version_count": len(crypto_key_versions),
            }

        except Exception as e:
            _LOGGER.error(f"Error processing CryptoKey data: {e}", exc_info=True)
            return None

    def _get_crypto_key_versions(
        self, crypto_key_name: str, kms_connector: KMSConnector
    ) -> List[Dict]:
        """
        List and process CryptoKeyVersion list for a specific CryptoKey.

        Args:
            crypto_key_name: Full name of the CryptoKey
            kms_connector: KMS connector instance

        Returns:
            list: Processed CryptoKeyVersion list
        """
        try:
            raw_versions = kms_connector.list_crypto_key_versions(crypto_key_name)
            processed_versions = []

            for version in raw_versions:
                processed_version = self._process_crypto_key_version_data(version)
                if processed_version:
                    processed_versions.append(processed_version)

            return processed_versions

        except Exception as e:
            _LOGGER.warning(
                f"Error collecting crypto key versions for {crypto_key_name}: {e}"
            )
            return []

    def _process_crypto_key_version_data(self, version: Dict) -> Optional[Dict]:
        """
        Process CryptoKeyVersion data.

        Args:
            version: Original CryptoKeyVersion data

        Returns:
            dict: Processed CryptoKeyVersion data
        """
        try:
            name = version.get("name", "")
            state = version.get("state", "")
            create_time = version.get("createTime", "")
            generate_time = version.get("generateTime", "")
            protection_level = version.get("protectionLevel", "")
            algorithm = version.get("algorithm", "")
            destroy_time = version.get("destroyTime", "")
            destroy_event_time = version.get("destroyEventTime", "")
            import_job = version.get("importJob", "")
            import_time = version.get("importTime", "")
            import_failure_reason = version.get("importFailureReason", "")
            reimport_eligible = str(version.get("reimportEligible", False))

            version_id = name.split("/")[-1] if name else ""

            return {
                "name": name,
                "version_id": version_id,
                "state": state,
                "create_time": create_time,
                "generate_time": generate_time,
                "protection_level": protection_level,
                "algorithm": algorithm,
                "destroy_time": destroy_time,
                "destroy_event_time": destroy_event_time,
                "import_job": import_job,
                "import_time": import_time,
                "import_failure_reason": import_failure_reason,
                "reimport_eligible": reimport_eligible,
            }

        except Exception as e:
            _LOGGER.error(f"Error processing CryptoKeyVersion data: {e}", exc_info=True)
            return None
