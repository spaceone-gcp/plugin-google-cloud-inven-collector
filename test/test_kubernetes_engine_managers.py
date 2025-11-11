"""KubernetesEngine 도메인 매니저들의 단위 테스트."""

import unittest
from unittest.mock import Mock, patch

# KubernetesEngine 매니저들 임포트
from spaceone.inventory.manager.kubernetes_engine.cluster_v1_manager import (
    GKEClusterV1Manager,
)
from spaceone.inventory.manager.kubernetes_engine.cluster_v1beta_manager import (
    GKEClusterV1BetaManager,
)


class TestGKEClusterV1Manager(unittest.TestCase):
    """GKEClusterV1Manager 테스트 클래스."""

    def setUp(self):
        """테스트 설정."""
        self.manager = GKEClusterV1Manager()
        self.mock_params = {"secret_data": {"project_id": "test-project-id"}}

    def test_list_clusters_success(self):
        """클러스터 목록 조회 성공 테스트."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_clusters.return_value = [
                {"name": "cluster1", "location": "us-central1"},
                {"name": "cluster2", "location": "us-east1"},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_clusters(self.mock_params)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_list_node_pools_success(self):
        """노드풀 목록 조회 성공 테스트."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_node_pools.return_value = [
                {"name": "pool1", "config": {"machineType": "e2-medium"}},
                {"name": "pool2", "config": {"machineType": "e2-standard-2"}},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_node_pools(
                "test-cluster", "us-central1", self.mock_params
            )

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_get_cluster_success(self):
        """클러스터 조회 성공 테스트."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.get_cluster.return_value = {
                "name": "test-cluster",
                "location": "us-central1",
                "status": "RUNNING",
            }
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.get_cluster(
                "test-cluster", "us-central1", self.mock_params
            )

            self.assertIsInstance(result, dict)
            self.assertEqual(result["name"], "test-cluster")

    def test_list_operations_success(self):
        """작업 목록 조회 성공 테스트."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_operations.return_value = [
                {"name": "op1", "status": "DONE"},
                {"name": "op2", "status": "RUNNING"},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_operations(self.mock_params)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_get_cluster_empty_result(self):
        """클러스터 조회 결과가 비어있는 경우 테스트."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.get_cluster.return_value = None
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.get_cluster(
                "test-cluster", "us-central1", self.mock_params
            )

            self.assertEqual(result, {})


class TestGKEClusterV1BetaManager(unittest.TestCase):
    """GKEClusterV1BetaManager 테스트 클래스."""

    def setUp(self):
        """테스트 설정."""
        self.manager = GKEClusterV1BetaManager()
        self.mock_params = {"secret_data": {"project_id": "test-project-id"}}

    def test_list_clusters_success(self):
        """클러스터 목록 조회 성공 테스트 (v1beta1)."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_clusters.return_value = [
                {"name": "cluster1", "location": "us-central1"},
                {"name": "cluster2", "location": "us-east1"},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_clusters(self.mock_params)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_list_node_pools_success(self):
        """노드풀 목록 조회 성공 테스트 (v1beta1)."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_node_pools.return_value = [
                {"name": "pool1", "config": {"machineType": "e2-medium"}},
                {"name": "pool2", "config": {"machineType": "e2-standard-2"}},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_node_pools(
                "test-cluster", "us-central1", self.mock_params
            )

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_get_cluster_success(self):
        """클러스터 조회 성공 테스트 (v1beta1)."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.get_cluster.return_value = {
                "name": "test-cluster",
                "location": "us-central1",
                "status": "RUNNING",
            }
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.get_cluster(
                "test-cluster", "us-central1", self.mock_params
            )

            self.assertIsInstance(result, dict)
            self.assertEqual(result["name"], "test-cluster")

    def test_list_operations_success(self):
        """작업 목록 조회 성공 테스트 (v1beta1)."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_operations.return_value = [
                {"name": "op1", "status": "DONE"},
                {"name": "op2", "status": "RUNNING"},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_operations(self.mock_params)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_list_fleets_success(self):
        """Fleet 목록 조회 성공 테스트 (v1beta1)."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_fleets.return_value = [
                {"name": "fleet1", "displayName": "Fleet 1"},
                {"name": "fleet2", "displayName": "Fleet 2"},
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_fleets(self.mock_params)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_list_memberships_success(self):
        """Membership 목록 조회 성공 테스트 (v1beta1)."""
        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_memberships.return_value = [
                {
                    "name": "membership1",
                    "endpoint": {"gkeCluster": {"resourceLink": "link1"}},
                },
                {
                    "name": "membership2",
                    "endpoint": {"gkeCluster": {"resourceLink": "link2"}},
                },
            ]
            mock_locator.get_connector.return_value = mock_connector

            result = self.manager.list_memberships(self.mock_params)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)

    def test_addons_config_processing(self):
        """addonsConfig 처리 테스트."""
        # 실제 GKE API 응답과 유사한 addonsConfig 구조
        mock_cluster = {
            "name": "test-cluster",
            "location": "us-central1",
            "status": "RUNNING",
            "addonsConfig": {
                "httpLoadBalancing": {"disabled": False},
                "horizontalPodAutoscaling": {"disabled": False},
                "kubernetesDashboard": {"disabled": True},
                "networkPolicyConfig": {"disabled": False},
                "cloudRunConfig": {
                    "disabled": True,
                    "loadBalancerType": "LOAD_BALANCER_TYPE_EXTERNAL",
                },
                "dnsCacheConfig": {"enabled": True},
                "configConnectorConfig": {"enabled": False},
                "gcePersistentDiskCsiDriverConfig": {"enabled": True},
            },
        }

        with patch.object(self.manager, "locator") as mock_locator:
            mock_connector = Mock()
            mock_connector.list_clusters.return_value = [mock_cluster]
            mock_connector.get_resource_limits.return_value = []
            mock_connector.list_fleets.return_value = []
            mock_connector.list_memberships.return_value = []
            mock_connector.list_node_pools.return_value = []
            mock_locator.get_connector.return_value = mock_connector

            # collect_cloud_service 메서드 테스트
            with (
                patch.object(
                    self.manager, "set_google_cloud_monitoring"
                ) as mock_monitoring,
                patch.object(self.manager, "set_google_cloud_logging") as mock_logging,
                patch.object(self.manager, "convert_labels_format") as mock_labels,
                patch.object(self.manager, "set_region_code") as mock_region,
            ):
                mock_monitoring.return_value = {}
                mock_logging.return_value = {}
                mock_labels.return_value = {}

                collected_services, error_responses = (
                    self.manager.collect_cloud_service(self.mock_params)
                )

                # 수집된 서비스가 있는지 확인
                self.assertEqual(len(collected_services), 1)
                self.assertEqual(len(error_responses), 0)

                # addonsConfig가 제대로 처리되었는지 확인
                cluster_resource = collected_services[0].resource
                cluster_data = cluster_resource.data

                # addonsConfig가 존재하는지 확인
                self.assertIn("addonsConfig", cluster_data)

                # 현재 구현의 문제점 확인 - str() 변환으로 인한 데이터 손실
                addons_config = cluster_data["addonsConfig"]
                print("\n=== addonsConfig 처리 결과 ===")
                print(f"Type: {type(addons_config)}")
                print(f"Content: {addons_config}")

                # 각 애드온별 확인
                for addon_key in [
                    "httpLoadBalancing",
                    "horizontalPodAutoscaling",
                    "kubernetesDashboard",
                    "networkPolicyConfig",
                ]:
                    if addon_key in addons_config:
                        addon_value = addons_config[addon_key]
                        print(f"{addon_key}: {addon_value} (type: {type(addon_value)})")

                        # 현재 구현에서는 str()로 변환되어 문자열이 됨
                        if isinstance(addon_value, str) and addon_value.startswith("{"):
                            print(f"  ⚠️  {addon_key}가 딕셔너리에서 문자열로 변환됨!")

                # 원본 데이터와 비교
                original_addons = mock_cluster["addonsConfig"]
                print("\n=== 원본 addonsConfig ===")
                for key, value in original_addons.items():
                    print(f"{key}: {value} (type: {type(value)})")

    def test_addons_config_data_structure(self):
        """addonsConfig 데이터 구조 분석 테스트."""
        # 다양한 addonsConfig 구조 테스트
        test_cases = [
            {
                "name": "basic_addons",
                "addonsConfig": {
                    "httpLoadBalancing": {"disabled": False},
                    "horizontalPodAutoscaling": {"disabled": True},
                    "kubernetesDashboard": {"disabled": True},
                    "networkPolicyConfig": {"disabled": False},
                },
            },
            {
                "name": "extended_addons",
                "addonsConfig": {
                    "httpLoadBalancing": {"disabled": False},
                    "horizontalPodAutoscaling": {"disabled": False},
                    "kubernetesDashboard": {"disabled": True},
                    "networkPolicyConfig": {"disabled": False},
                    "cloudRunConfig": {
                        "disabled": False,
                        "loadBalancerType": "LOAD_BALANCER_TYPE_EXTERNAL",
                    },
                    "dnsCacheConfig": {"enabled": True},
                    "configConnectorConfig": {"enabled": False},
                    "gcePersistentDiskCsiDriverConfig": {"enabled": True},
                    "istioConfig": {"disabled": False, "auth": "AUTH_MUTUAL_TLS"},
                },
            },
        ]

        for test_case in test_cases:
            print(f"\n=== 테스트 케이스: {test_case['name']} ===")
            addons_config = test_case["addonsConfig"]

            # 현재 manager의 처리 방식 시뮬레이션
            processed_addons = {}
            for key in [
                "httpLoadBalancing",
                "horizontalPodAutoscaling",
                "kubernetesDashboard",
                "networkPolicyConfig",
            ]:
                original_value = addons_config.get(key, {})
                processed_value = str(original_value)  # 현재 구현
                processed_addons[key] = processed_value

                print(f"{key}:")
                print(f"  원본: {original_value} (타입: {type(original_value)})")
                print(f"  처리후: {processed_value} (타입: {type(processed_value)})")

                # 데이터 손실 확인
                if isinstance(original_value, dict) and processed_value.startswith("{"):
                    print("  ❌ 딕셔너리가 문자열로 변환되어 데이터 손실 발생!")

            # 올바른 처리 방식
            correct_addons = {}
            for key, value in addons_config.items():
                if isinstance(value, dict):
                    correct_addons[key] = value  # 딕셔너리는 그대로 유지
                else:
                    correct_addons[key] = str(value)  # 다른 타입만 문자열로 변환

            print("\n올바른 처리 결과:")
            for key, value in correct_addons.items():
                print(f"  {key}: {value} (타입: {type(value)})")


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
