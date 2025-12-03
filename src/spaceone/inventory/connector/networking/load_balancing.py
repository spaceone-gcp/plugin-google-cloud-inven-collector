import logging

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["LoadBalancingConnector"]
_LOGGER = logging.getLogger(__name__)


class LoadBalancingConnector(GoogleCloudConnector):
    google_client_service = "compute"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
        self.client = self._build_client(self.google_client_service, self.version)

    def list_url_maps(self, **query):
        url_map_list = []
        query.update({"project": self.project_id})
        request = self.client.urlMaps().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, url_scoped_list in response["items"].items():
                if "urlMaps" in url_scoped_list:
                    url_map_list.extend(url_scoped_list.get("urlMaps"))
            request = self.client.urlMaps().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return url_map_list

    def list_backend_services(self, **query):
        backend_svc_list = []
        query.update({"project": self.project_id})
        request = self.client.backendServices().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, url_scoped_list in response["items"].items():
                if "backendServices" in url_scoped_list:
                    backend_svc_list.extend(url_scoped_list.get("backendServices"))
            request = self.client.backendServices().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return backend_svc_list

    def list_target_pools(self, **query):
        target_pool_list = []
        query.update({"project": self.project_id})
        request = self.client.targetPools().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, pool_scoped_list in response["items"].items():
                if "targetPools" in pool_scoped_list:
                    target_pool_list.extend(pool_scoped_list.get("targetPools"))
            request = self.client.targetPools().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return target_pool_list

    def list_forwarding_rules(self, **query):
        forwarding_rule_list = []
        query.update({"project": self.project_id})
        request = self.client.forwardingRules().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, forwarding_scoped_list in response["items"].items():
                if "forwardingRules" in forwarding_scoped_list:
                    forwarding_rule_list.extend(
                        forwarding_scoped_list.get("forwardingRules")
                    )
            request = self.client.forwardingRules().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return forwarding_rule_list

    def list_tcp_proxies(self, **query):
        tcp_proxy_list = []
        query.update({"project": self.project_id})
        request = self.client.targetTcpProxies().list(**query)
        while request is not None:
            response = request.execute()
            for tcp_proxy in response.get("items", []):
                tcp_proxy_list.append(tcp_proxy)
            request = self.client.targetTcpProxies().list_next(
                previous_request=request, previous_response=response
            )

        return tcp_proxy_list

    def list_ssl_proxies(self, **query):
        ssl_proxy_list = []
        query.update({"project": self.project_id})
        request = self.client.targetSslProxies().list(**query)
        while request is not None:
            response = request.execute()
            for ssl_proxy in response.get("items", []):
                ssl_proxy_list.append(ssl_proxy)
            request = self.client.targetSslProxies().list_next(
                previous_request=request, previous_response=response
            )

        return ssl_proxy_list

    def list_grpc_proxies(self, **query):
        grpc_proxy_list = []
        query.update({"project": self.project_id})
        request = self.client.targetGrpcProxies().list(**query)
        while request is not None:
            response = request.execute()
            for grpc_proxy in response.get("items", []):
                grpc_proxy_list.append(grpc_proxy)
            request = self.client.targetGrpcProxies().list_next(
                previous_request=request, previous_response=response
            )

        return grpc_proxy_list

    def list_backend_buckets(self, **query):
        bucket_bucket_list = []
        query.update({"project": self.project_id})
        request = self.client.backendBuckets().list(**query)
        while request is not None:
            response = request.execute()
            for backend_bucket in response.get("items", []):
                bucket_bucket_list.append(backend_bucket)
            request = self.client.backendBuckets().list_next(
                previous_request=request, previous_response=response
            )

        return bucket_bucket_list

    def list_target_http_proxies(self, **query):
        http_proxy_list = []
        query.update({"project": self.project_id})
        request = self.client.targetHttpProxies().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, thp_list in response["items"].items():
                if "targetHttpProxies" in thp_list:
                    http_proxy_list.extend(thp_list.get("targetHttpProxies"))
            request = self.client.targetHttpProxies().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return http_proxy_list

    def list_target_https_proxies(self, **query):
        https_proxy_list = []
        query.update({"project": self.project_id})
        request = self.client.targetHttpsProxies().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, hp_list in response["items"].items():
                if "targetHttpsProxies" in hp_list:
                    https_proxy_list.extend(hp_list.get("targetHttpsProxies"))
            request = self.client.targetHttpsProxies().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return https_proxy_list

    def list_ssl_certificates(self, **query):
        ssl_certificate_list = []
        query.update({"project": self.project_id})
        request = self.client.sslCertificates().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, sc_list in response["items"].items():
                if "sslCertificates" in sc_list:
                    ssl_certificate_list.extend(sc_list.get("sslCertificates"))
            request = self.client.sslCertificates().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return ssl_certificate_list

    def list_health_checks(self, **query):
        health_check_list = []
        query.update({"project": self.project_id})
        request = self.client.healthChecks().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, hc_list in response["items"].items():
                if "healthChecks" in hc_list:
                    health_check_list.extend(hc_list.get("healthChecks"))
            request = self.client.healthChecks().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return health_check_list

    def list_http_health_checks(self, **query):
        http_health_list = []
        query.update({"project": self.project_id})
        request = self.client.httpHealthChecks().list(**query)
        while request is not None:
            response = request.execute()
            for backend_bucket in response.get("items", []):
                http_health_list.append(backend_bucket)
            request = self.client.httpHealthChecks().list_next(
                previous_request=request, previous_response=response
            )

        return http_health_list

    def list_https_health_checks(self, **query):
        https_health_list = []
        query.update({"project": self.project_id})
        request = self.client.httpsHealthChecks().list(**query)
        while request is not None:
            response = request.execute()
            for backend_bucket in response.get("items", []):
                https_health_list.append(backend_bucket)
            request = self.client.httpsHealthChecks().list_next(
                previous_request=request, previous_response=response
            )

        return https_health_list

    def list_instance_groups(self, **query):
        instance_group_list = []
        query.update({"project": self.project_id})
        request = self.client.instanceGroupManagers().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, ig_list in response["items"].items():
                if "instanceGroupManagers" in ig_list:
                    instance_group_list.extend(ig_list.get("instanceGroupManagers"))
            request = self.client.instanceGroupManagers().aggregatedList_next(
                previous_request=request, previous_response=response
            )

        return instance_group_list

    def list_autoscalers(self, **query):
        autoscaler_list = []
        query.update({"project": self.project_id})
        request = self.client.autoscalers().aggregatedList(**query)
        while request is not None:
            response = request.execute()
            for key, as_list in response["items"].items():
                if "autoscalers" in as_list:
                    autoscaler_list.extend(as_list.get("autoscalers"))
            request = self.client.autoscalers().aggregatedList_next(
                previous_request=request, previous_response=response
            )
        return autoscaler_list

    def get_target_proxy(
        self, project_id: str, region: str, proxy_type: str, proxy_name: str
    ):
        """
        특정 Target Proxy의 상세 정보를 가져옵니다.

        Args:
            project_id: 프로젝트 ID
            region: 지역 (global일 수도 있음)
            proxy_type: Target Proxy 타입 (targetHttpProxies, targetHttpsProxies 등)
            proxy_name: Target Proxy 이름

        Returns:
            Target Proxy 상세 정보 딕셔너리
        """
        try:
            # Proxy 타입에 따라 적절한 API 메서드 선택
            if proxy_type == "targetHttpProxies":
                if region and region != "global":
                    # Regional HTTP Proxy
                    request = self.client.regionTargetHttpProxies().get(
                        project=project_id, region=region, targetHttpProxy=proxy_name
                    )
                else:
                    # Global HTTP Proxy
                    request = self.client.targetHttpProxies().get(
                        project=project_id, targetHttpProxy=proxy_name
                    )
            elif proxy_type == "targetHttpsProxies":
                if region and region != "global":
                    # Regional HTTPS Proxy
                    request = self.client.regionTargetHttpsProxies().get(
                        project=project_id, region=region, targetHttpsProxy=proxy_name
                    )
                else:
                    # Global HTTPS Proxy
                    request = self.client.targetHttpsProxies().get(
                        project=project_id, targetHttpsProxy=proxy_name
                    )
            elif proxy_type == "targetTcpProxies":
                # TCP Proxy는 Global만 지원
                request = self.client.targetTcpProxies().get(
                    project=project_id, targetTcpProxy=proxy_name
                )
            elif proxy_type == "targetSslProxies":
                # SSL Proxy는 Global만 지원
                request = self.client.targetSslProxies().get(
                    project=project_id, targetSslProxy=proxy_name
                )
            elif proxy_type == "targetGrpcProxies":
                if region and region != "global":
                    # Regional gRPC Proxy
                    request = self.client.regionTargetGrpcProxies().get(
                        project=project_id, region=region, targetGrpcProxy=proxy_name
                    )
                else:
                    # Global gRPC Proxy
                    request = self.client.targetGrpcProxies().get(
                        project=project_id, targetGrpcProxy=proxy_name
                    )
            else:
                _LOGGER.warning(f"Unsupported proxy type: {proxy_type}")
                return None

            response = request.execute()
            return response

        except Exception as e:
            _LOGGER.warning(
                f"Failed to get target proxy {proxy_name} of type {proxy_type}: {e}"
            )
            return None
