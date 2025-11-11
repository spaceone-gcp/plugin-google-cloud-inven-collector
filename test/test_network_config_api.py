"""GKE Cluster 및 NodePool networkConfig API 응답 테스트 스크립트.

실제 GCP API 응답을 확인하여 networkConfig의 모든 필드를 검증합니다.
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
        _LOGGER.info("Please create conf/client_secret.json with your GCP credentials")
        return None

    with open(secret_file, "r") as f:
        return json.load(f)


def test_cluster_api_response():
    """실제 GKE 클러스터 API 응답을 테스트합니다."""
    secret_data = load_secret_data()
    if not secret_data:
        return

    try:
        # Google API 클라이언트 직접 생성
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
        cluster_list = []
        request = (
            client.projects()
            .locations()
            .clusters()
            .list(parent=f"projects/{project_id}/locations/-")
        )
        while request is not None:
            response = request.execute()
            if "clusters" in response:
                cluster_list.extend(response.get("clusters", []))
            try:
                request = (
                    client.projects()
                    .locations()
                    .clusters()
                    .list_next(previous_request=request, previous_response=response)
                )
            except AttributeError:
                break
        clusters = cluster_list

        if not clusters:
            _LOGGER.warning("No clusters found")
            return

        _LOGGER.info(f"Found {len(clusters)} clusters")

        # 첫 번째 클러스터의 networkConfig 상세 분석
        for idx, cluster in enumerate(clusters[:1]):  # 첫 번째 클러스터만 분석
            cluster_name = cluster.get("name", "unknown")
            cluster_location = cluster.get("location", "unknown")

            _LOGGER.info(f"\n{'=' * 80}")
            _LOGGER.info(f"Cluster {idx + 1}: {cluster_name} ({cluster_location})")
            _LOGGER.info(f"{'=' * 80}")

            # 전체 클러스터 정보 출력 (networkConfig 포함)
            if "networkConfig" in cluster:
                network_config = cluster["networkConfig"]
                _LOGGER.info("\n=== networkConfig 전체 구조 ===")
                _LOGGER.info(json.dumps(network_config, indent=2, default=str))

                _LOGGER.info("\n=== networkConfig 필드별 상세 분석 ===")
                for key, value in network_config.items():
                    _LOGGER.info(f"  {key}: {value} (type: {type(value).__name__})")

                # 현재 코드에서 처리하는 필드들 (최근 추가한 필드 포함)
                current_fields = [
                    "network",
                    "subnetwork",
                    "enableIntraNodeVisibility",
                    "enableL4ilbSubsetting",
                    "podRange",  # 최근 추가
                    "podIpv4CidrBlock",  # 최근 추가
                    "enablePrivateNodes",  # 최근 추가
                    "networkTierConfig",  # 최근 추가
                ]

                # API 응답에 있는 모든 필드
                api_fields = list(network_config.keys())

                _LOGGER.info("\n=== 필드 비교 ===")
                _LOGGER.info(f"현재 코드에서 처리하는 필드: {current_fields}")
                _LOGGER.info(f"API 응답에 있는 필드: {api_fields}")

                # 누락된 필드 확인 (API에 있지만 코드에서 처리하지 않는 필드)
                missing_fields = set(api_fields) - set(current_fields)
                if missing_fields:
                    _LOGGER.warning(
                        f"\n⚠️  API에 있지만 코드에서 처리하지 않는 필드들: {missing_fields}"
                    )
                    for field in missing_fields:
                        _LOGGER.warning(
                            f"  - {field}: {network_config.get(field)} (type: {type(network_config.get(field)).__name__})"
                        )

                # 존재하지 않는 필드 확인 (코드에서 처리하지만 API에 없는 필드)
                non_existent_fields = set(current_fields) - set(api_fields)
                if non_existent_fields:
                    _LOGGER.error(
                        f"\n❌ 코드에서 처리하지만 API 응답에 없는 필드들: {non_existent_fields}"
                    )
                    _LOGGER.error(
                        "  → 이 필드들은 API 응답에 없으므로 제거해야 합니다!"
                    )
                else:
                    _LOGGER.info("\n✅ 모든 필드가 API 응답에 존재합니다")

                # 최근 추가한 필드들의 존재 여부 확인
                recently_added_fields = [
                    "podRange",
                    "podIpv4CidrBlock",
                    "enablePrivateNodes",
                    "networkTierConfig",
                ]
                _LOGGER.info("\n=== 최근 추가한 필드들의 존재 여부 ===")
                for field in recently_added_fields:
                    if field in api_fields:
                        _LOGGER.info(
                            f"  ✅ {field}: 존재함 - {network_config.get(field)}"
                        )
                    else:
                        _LOGGER.warning(
                            f"  ❌ {field}: API 응답에 없음 - 코드에서 제거 필요!"
                        )

            else:
                _LOGGER.warning("networkConfig가 클러스터 응답에 없습니다")

            # 전체 클러스터 구조도 출력 (참고용)
            _LOGGER.info("\n=== 클러스터 전체 키 목록 ===")
            _LOGGER.info(f"Keys: {list(cluster.keys())}")

            # networkConfig 관련 다른 필드들도 확인
            network_related_keys = [
                key
                for key in cluster.keys()
                if "network" in key.lower() or "ip" in key.lower()
            ]
            if network_related_keys:
                _LOGGER.info(f"\n네트워크 관련 필드들: {network_related_keys}")

    except Exception as e:
        _LOGGER.error(f"Error testing API response: {e}", exc_info=True)


def test_specific_cluster(cluster_name: str, location: str):
    """특정 클러스터의 상세 정보를 조회합니다."""
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

        _LOGGER.info(f"Fetching cluster: {cluster_name} in {location}")
        request = (
            client.projects()
            .locations()
            .clusters()
            .get(
                name=f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
            )
        )
        cluster = request.execute()

        if not cluster:
            _LOGGER.error(f"Cluster not found: {cluster_name}")
            return

        _LOGGER.info(f"\n{'=' * 80}")
        _LOGGER.info(f"Cluster: {cluster_name}")
        _LOGGER.info(f"{'=' * 80}")

        if "networkConfig" in cluster:
            network_config = cluster["networkConfig"]
            _LOGGER.info("\n=== networkConfig 전체 구조 ===")
            print(json.dumps(network_config, indent=2, default=str))

    except Exception as e:
        _LOGGER.error(f"Error fetching cluster: {e}", exc_info=True)


def test_nodepool_api_response():
    """실제 GKE NodePool API 응답을 테스트합니다."""
    secret_data = load_secret_data()
    if not secret_data:
        return

    try:
        # Google API 클라이언트 직접 생성
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
        cluster_list = []
        request = (
            client.projects()
            .locations()
            .clusters()
            .list(parent=f"projects/{project_id}/locations/-")
        )
        while request is not None:
            response = request.execute()
            if "clusters" in response:
                cluster_list.extend(response.get("clusters", []))
            try:
                request = (
                    client.projects()
                    .locations()
                    .clusters()
                    .list_next(previous_request=request, previous_response=response)
                )
            except AttributeError:
                break
        clusters = cluster_list

        if not clusters:
            _LOGGER.warning("No clusters found")
            return

        _LOGGER.info(f"Found {len(clusters)} clusters")

        # 첫 번째 클러스터의 NodePool networkConfig 상세 분석
        for idx, cluster in enumerate(clusters[:1]):  # 첫 번째 클러스터만 분석
            cluster_name = cluster.get("name", "unknown")
            cluster_location = cluster.get("location", "unknown")

            _LOGGER.info(f"\n{'=' * 80}")
            _LOGGER.info(f"Cluster {idx + 1}: {cluster_name} ({cluster_location})")
            _LOGGER.info(f"{'=' * 80}")

            # NodePool 목록 조회
            _LOGGER.info(f"\nFetching NodePools for cluster {cluster_name}...")
            nodepool_request = (
                client.projects()
                .locations()
                .clusters()
                .nodePools()
                .list(
                    parent=f"projects/{project_id}/locations/{cluster_location}/clusters/{cluster_name}"
                )
            )
            nodepool_response = nodepool_request.execute()
            node_pools = nodepool_response.get("nodePools", [])

            if not node_pools:
                _LOGGER.warning(f"No node pools found for cluster {cluster_name}")
                continue

            _LOGGER.info(f"Found {len(node_pools)} node pools")

            # 첫 번째 NodePool의 networkConfig 상세 분석
            for pool_idx, node_pool in enumerate(
                node_pools[:1]
            ):  # 첫 번째 NodePool만 분석
                node_pool_name = node_pool.get("name", "unknown")

                _LOGGER.info(f"\n{'=' * 80}")
                _LOGGER.info(
                    f"NodePool {pool_idx + 1}: {node_pool_name} (Cluster: {cluster_name})"
                )
                _LOGGER.info(f"{'=' * 80}")

                # 전체 NodePool 정보 출력 (networkConfig 포함)
                if "networkConfig" in node_pool:
                    network_config = node_pool["networkConfig"]
                    _LOGGER.info("\n=== networkConfig 전체 구조 ===")
                    _LOGGER.info(json.dumps(network_config, indent=2, default=str))

                    _LOGGER.info("\n=== networkConfig 필드별 상세 분석 ===")
                    for key, value in network_config.items():
                        _LOGGER.info(f"  {key}: {value} (type: {type(value).__name__})")

                    # 현재 코드에서 처리하는 필드들
                    current_fields = [
                        "podRange",
                        "podIpv4CidrBlock",
                        "createPodRange",
                        "enablePrivateNodes",
                    ]

                    # API 응답에 있는 모든 필드
                    api_fields = list(network_config.keys())

                    _LOGGER.info("\n=== 필드 비교 ===")
                    _LOGGER.info(f"현재 코드에서 처리하는 필드: {current_fields}")
                    _LOGGER.info(f"API 응답에 있는 필드: {api_fields}")

                    # 불린 타입 필드 확인
                    boolean_fields = ["createPodRange", "enablePrivateNodes"]
                    _LOGGER.info("\n=== 불린 타입 필드 확인 ===")
                    for field in boolean_fields:
                        if field in network_config:
                            value = network_config[field]
                            value_type = type(value).__name__
                            _LOGGER.info(
                                f"  {field}: {value} (type: {value_type}) - "
                                f"{'✅ 불린 타입' if isinstance(value, bool) else '❌ 불린 타입 아님'}"
                            )
                        else:
                            _LOGGER.warning(f"  {field}: API 응답에 없음")

                    # 누락된 필드 확인 (API에 있지만 코드에서 처리하지 않는 필드)
                    missing_fields = set(api_fields) - set(current_fields)
                    if missing_fields:
                        _LOGGER.warning(
                            f"\n⚠️  API에 있지만 코드에서 처리하지 않는 필드들: {missing_fields}"
                        )
                        for field in missing_fields:
                            _LOGGER.warning(
                                f"  - {field}: {network_config.get(field)} (type: {type(network_config.get(field)).__name__})"
                            )

                    # 존재하지 않는 필드 확인 (코드에서 처리하지만 API에 없는 필드)
                    non_existent_fields = set(current_fields) - set(api_fields)
                    if non_existent_fields:
                        _LOGGER.error(
                            f"\n❌ 코드에서 처리하지만 API 응답에 없는 필드들: {non_existent_fields}"
                        )
                        _LOGGER.error(
                            "  → 이 필드들은 API 응답에 없으므로 제거해야 합니다!"
                        )
                    else:
                        _LOGGER.info("\n✅ 모든 필드가 API 응답에 존재합니다")

                else:
                    _LOGGER.warning(
                        f"networkConfig가 NodePool {node_pool_name} 응답에 없습니다"
                    )

                # 전체 NodePool 구조도 출력 (참고용)
                _LOGGER.info("\n=== NodePool 전체 키 목록 ===")
                _LOGGER.info(f"Keys: {list(node_pool.keys())}")

    except Exception as e:
        _LOGGER.error(f"Error testing NodePool API response: {e}", exc_info=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GKE Cluster 및 NodePool networkConfig API 테스트"
    )
    parser.add_argument(
        "--cluster-name", help="특정 클러스터 이름 (선택사항)", default=None
    )
    parser.add_argument("--location", help="클러스터 위치 (선택사항)", default=None)
    parser.add_argument(
        "--nodepool",
        action="store_true",
        help="NodePool networkConfig 테스트 (기본값: Cluster 테스트)",
    )

    args = parser.parse_args()

    if args.cluster_name and args.location:
        test_specific_cluster(args.cluster_name, args.location)
    elif args.nodepool:
        test_nodepool_api_response()
    else:
        test_cluster_api_response()
