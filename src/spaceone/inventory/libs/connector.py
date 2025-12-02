import logging
from functools import wraps

import google.oauth2.service_account
import google_auth_httplib2
import googleapiclient.discovery
import httplib2
from googleapiclient.http import HttpRequest

from spaceone.core.connector import BaseConnector
from spaceone.inventory.conf.client_config import ClientConfigManager

_LOGGER = logging.getLogger(__name__)


class GoogleCloudConnector(BaseConnector):
    google_client_service = "compute"
    version = "v1"

    def __init__(self, *args, **kwargs):
        """
        kwargs
            - schema
            - options
            - secret_data

        secret_data(dict)
            - type: ..
            - project_id: ...
            - token_uri: ...
            - ...
        """

        super().__init__(*args, **kwargs)
        secret_data = kwargs.get("secret_data")

        if not secret_data:
            raise ValueError("secret_data is required for GoogleCloudConnector")

        self.project_id = secret_data.get("project_id")

        if not self.project_id:
            raise ValueError("project_id is required in secret_data")

        try:
            # 인증 정보 생성 (Cloud Platform scope 추가)
            # credentials를 인스턴스 속성으로 저장하여 하위 클래스에서 재사용 가능
            self.credentials = (
                google.oauth2.service_account.Credentials.from_service_account_info(
                    secret_data,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            )

            # 타임아웃 및 재시도 설정 로드
            timeout = self.get_timeout()
            self.max_retry_attempts = self.get_max_retry_attempts()

            # HTTP 클라이언트 생성 (타임아웃 적용)
            http = httplib2.Http(timeout=timeout)

            # 인증된 HTTP 클라이언트 생성
            authorized_http = google_auth_httplib2.AuthorizedHttp(
                self.credentials, http=http
            )

            # API 클라이언트 생성 (인증된 http만 전달)
            self.client = googleapiclient.discovery.build(
                self.google_client_service,
                self.version,
                http=authorized_http,
                cache_discovery=False,
            )

            # HttpRequest.execute()에 num_retries 자동 주입
            self._patch_execute_method()

        except Exception as e:
            _LOGGER.error(f"Failed to initialize: {e}")
            raise ValueError(f"Invalid credentials: {e}") from e

    def _patch_execute_method(self):
        """HttpRequest.execute()에 num_retries를 자동 주입하는 monkey patch"""
        if hasattr(HttpRequest.execute, "_is_patched"):
            return

        original_execute = HttpRequest.execute
        default_num_retries = self.max_retry_attempts

        @wraps(original_execute)
        def execute_with_default_retries(request_self, http=None, num_retries=None):
            if num_retries is None:
                num_retries = default_num_retries

            # float를 int로 변환 (API에서 5.0으로 올 수 있음)
            num_retries = int(num_retries)

            # googleapiclient 기본 재시도 사용
            return original_execute(request_self, http, num_retries)

        execute_with_default_retries._is_patched = True
        HttpRequest.execute = execute_with_default_retries

    def verify(self, **kwargs):
        if self.client is None:
            self.set_connect(**kwargs)

    def generate_query(self, **query):
        query.update(
            {
                "project": self.project_id,
            }
        )
        return query

    def get_max_retry_attempts(self) -> int:
        """최대 재시도 횟수 반환"""
        return ClientConfigManager.get_config().get_max_retry_attempts()

    def get_timeout(self) -> int:
        """HTTP 타임아웃 설정 반환 (초)"""
        return ClientConfigManager.get_config().get_timeout()

    def _build_client(self, service_name: str, version: str):
        """
        타임아웃과 재시도 설정이 적용된 Google API 클라이언트를 생성합니다.

        자식 클래스에서 다른 서비스의 클라이언트가 필요할 때 이 메서드를 사용하세요.

        Args:
            service_name: Google API 서비스 이름 (예: 'container', 'appengine', 'dataproc')
            version: API 버전 (예: 'v1', 'v1beta1')

        Returns:
            googleapiclient.discovery.Resource: 생성된 API 클라이언트
        """
        timeout = self.get_timeout()

        # HTTP 클라이언트 생성 (타임아웃 적용)
        http = httplib2.Http(timeout=timeout)

        # 인증된 HTTP 클라이언트 생성
        authorized_http = google_auth_httplib2.AuthorizedHttp(
            self.credentials, http=http
        )

        # API 클라이언트 생성
        return googleapiclient.discovery.build(
            service_name,
            version,
            http=authorized_http,
            cache_discovery=False,
        )

    def list_zones(self, **query):
        """zone 목록 조회"""
        query = self.generate_query(**query)
        request = self.client.zones().list(**query)
        result = request.execute()
        return result.get("items", [])
