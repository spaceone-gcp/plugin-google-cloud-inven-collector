"""GKE NodePool labels API 응답 테스트 스크립트.

실제 GCP API 응답을 확인하여 NodePool의 labels 필드 존재 여부를 검증합니다.
"""

import json
import logging
from pathlib import Path

import google.oauth2.service_account
import googleapiclient.discovery

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
_LOGGER = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent


def load_secret_data():
    """secret_data를 로드합니다."""
    secret_file = project_root / "conf" / "google_client_secret.json"
    if not secret_file.exists():
        _LOGGER.error(f"Secret file not found: {secret_file}")
        _LOGGER.info(
            "Please create conf/google_client_secret.json with your GCP credentials"
        )
        return None

    with open(secret_file, "r") as f:
        return json.load(f)


def test_nodepool_labels():
    """실제 GKE NodePool API 응답에서 labels 필드를 확인합니다."""
    secret_data = load_secret_data()
    if not secret_data:
        return

    try:
        project_id = secret_data.get("project_id")
        credentials = (
            google.oauth2.service_account.Credentials.from_service_account_info(
                secret_data
            )
        )
        client = googleapiclient.discovery.build(
            "container", "v1beta1", credentials=credentials
        )

        # 클러스터 목록 조회
        _LOGGER.info("Fetching GKE clusters...")
        request = (
            client.projects()
            .locations()
            .clusters()
            .list(parent=f"projects/{project_id}/locations/-")
        )
        response = request.execute()
        clusters = response.get("clusters", [])

        if not clusters:
            _LOGGER.warning("No clusters found")
            return

        # 첫 번째 클러스터의 NodePool 조회
        cluster = clusters[0]
        cluster_name = cluster.get("name")
        cluster_location = cluster.get("location")

        _LOGGER.info(f"\n{'=' * 80}")
        _LOGGER.info(f"Testing cluster: {cluster_name} ({cluster_location})")
        _LOGGER.info(f"{'=' * 80}")

        # NodePool 목록 조회
        request = (
            client.projects()
            .locations()
            .clusters()
            .nodePools()
            .list(
                parent=f"projects/{project_id}/locations/{cluster_location}/clusters/{cluster_name}"
            )
        )
        response = request.execute()
        node_pools = response.get("nodePools", [])

        if not node_pools:
            _LOGGER.warning("No node pools found")
            return

        _LOGGER.info(f"Found {len(node_pools)} node pools")

        # 각 NodePool의 labels 확인
        for pool_idx, node_pool in enumerate(node_pools):
            pool_name = node_pool.get("name", "unknown")

            _LOGGER.info(f"\n{'=' * 80}")
            _LOGGER.info(f"NodePool {pool_idx + 1}: {pool_name}")
            _LOGGER.info(f"{'=' * 80}")

            # 전체 NodePool 키 목록
            _LOGGER.info("\n=== NodePool 전체 키 목록 ===")
            _LOGGER.info(f"Keys: {list(node_pool.keys())}")

            # 1. node_pool의 직접 labels 확인
            if "labels" in node_pool:
                labels = node_pool["labels"]
                _LOGGER.info("\n✅ node_pool.labels 필드가 API 응답에 있습니다!")
                _LOGGER.info(f"labels: {json.dumps(labels, indent=2)}")
                _LOGGER.info(f"Type: {type(labels)}")
                _LOGGER.info(f"Count: {len(labels) if isinstance(labels, dict) else 0}")
            else:
                _LOGGER.warning("\n❌ node_pool.labels 필드가 API 응답에 없습니다.")

            # 2. config.labels 확인
            if "config" in node_pool:
                config = node_pool["config"]
                _LOGGER.info("\n=== config 필드 확인 ===")
                _LOGGER.info(
                    f"config keys: {list(config.keys()) if isinstance(config, dict) else 'N/A'}"
                )

                if "labels" in config:
                    config_labels = config["labels"]
                    _LOGGER.info("\n✅ config.labels 필드가 API 응답에 있습니다!")
                    _LOGGER.info(
                        f"config.labels: {json.dumps(config_labels, indent=2)}"
                    )
                    _LOGGER.info(f"Type: {type(config_labels)}")
                    _LOGGER.info(
                        f"Count: {len(config_labels) if isinstance(config_labels, dict) else 0}"
                    )
                else:
                    _LOGGER.warning("\n❌ config.labels 필드가 API 응답에 없습니다.")

                if "resourceLabels" in config:
                    resource_labels = config["resourceLabels"]
                    _LOGGER.info(
                        "\n✅ config.resourceLabels 필드가 API 응답에 있습니다!"
                    )
                    _LOGGER.info(
                        f"config.resourceLabels: {json.dumps(resource_labels, indent=2)}"
                    )
                    _LOGGER.info(f"Type: {type(resource_labels)}")
                    _LOGGER.info(
                        f"Count: {len(resource_labels) if isinstance(resource_labels, dict) else 0}"
                    )
                else:
                    _LOGGER.warning(
                        "\n❌ config.resourceLabels 필드가 API 응답에 없습니다."
                    )
            else:
                _LOGGER.warning("\n❌ config 필드가 NodePool API 응답에 없습니다.")

            # 3. resourceLabels 확인 (클러스터와 유사한 패턴)
            if "resourceLabels" in node_pool:
                resource_labels = node_pool["resourceLabels"]
                _LOGGER.info("\n✅ resourceLabels 필드가 API 응답에 있습니다!")
                _LOGGER.info(f"resourceLabels: {json.dumps(resource_labels, indent=2)}")
            else:
                _LOGGER.info(
                    "\nℹ️ resourceLabels 필드가 API 응답에 없습니다. (정상일 수 있음)"
                )

            # 4. Manager 처리 시뮬레이션
            _LOGGER.info("\n=== Manager 처리 시뮬레이션 ===")
            all_labels = {}

            # node_pool에 직접 labels가 있는 경우
            if "labels" in node_pool:
                all_labels.update(node_pool.get("labels", {}))
                _LOGGER.info(
                    f"Added node_pool.labels: {len(node_pool.get('labels', {}))} labels"
                )

            # config.labels가 있는 경우 병합
            config_labels = node_pool.get("config", {}).get("labels", {})
            if config_labels:
                all_labels.update(config_labels)
                _LOGGER.info(f"Added config.labels: {len(config_labels)} labels")

            # config.resourceLabels가 있는 경우 병합 (GKE NodePool에서 주로 사용)
            config_resource_labels = node_pool.get("config", {}).get(
                "resourceLabels", {}
            )
            if config_resource_labels:
                all_labels.update(config_resource_labels)
                _LOGGER.info(
                    f"Added config.resourceLabels: {len(config_resource_labels)} labels"
                )

            _LOGGER.info(f"\nTotal labels collected: {len(all_labels)}")
            if all_labels:
                _LOGGER.info(f"Labels: {json.dumps(all_labels, indent=2)}")
            else:
                _LOGGER.warning("⚠️ No labels found in NodePool API response!")

    except Exception as e:
        _LOGGER.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    test_nodepool_labels()
