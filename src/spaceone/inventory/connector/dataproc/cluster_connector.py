import logging
import socket
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from googleapiclient.errors import HttpError

from spaceone.inventory.libs.connector import GoogleCloudConnector

__all__ = ["DataprocClusterConnector"]
logger = logging.getLogger(__name__)


class DataprocClusterConnector(GoogleCloudConnector):
    google_client_service = "dataproc"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._regions_cache = None
        self._cache_timestamp = 0
        self._client_lock = threading.Lock()  # Lock for thread safety
        self._thread_local = threading.local()  # Thread-specific independent client

    def verify(self, options: Dict[str, Any], secret_data: Dict[str, Any]) -> str:
        """
        Verify connection status.

        Args:
            options: Verification options
            secret_data: Google Cloud authentication information

        Returns:
            str: Connection status ("ACTIVE" or "INACTIVE")

        Raises:
            Exception: When connection fails
        """
        try:
            self.get_connect(secret_data)
            return "ACTIVE"
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            raise

    def get_connect(self, secret_data: Dict[str, Any]) -> None:
        """
        Initialize connection to Google Cloud Dataproc.

        Args:
            secret_data: Credentials for Google Cloud authentication
                - project_id: Google Cloud project ID
                - Other information required for service account authentication

        Raises:
            ValueError: When project_id is missing
            Exception: When authentication fails
        """
        if not secret_data.get("project_id"):
            raise ValueError("project_id is required in secret_data")

        self.project_id = secret_data.get("project_id")
        try:
            # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
            self.client = self._build_client("dataproc", "v1")
            logger.info("Successfully connected to Dataproc service")
        except ValueError as e:
            logger.error(f"Invalid service account credentials: {e}")
            raise
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Network error during Dataproc connection: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Dataproc connection: {e}")
            raise

    def _get_thread_safe_client(self):
        """
        Return thread-specific independent client instance.

        Returns:
            Thread-specific independent Google API client
        """
        if (
            not hasattr(self._thread_local, "client")
            or self._thread_local.client is None
        ):
            # Create independent client for each thread
            try:
                if hasattr(self, "credentials") and self.credentials:
                    # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
                    self._thread_local.client = self._build_client("dataproc", "v1")
                else:
                    # If main client exists, use it as fallback
                    if hasattr(self, "client") and self.client:
                        self._thread_local.client = self.client
                    else:
                        raise ValueError(
                            "No client or credentials available for thread-safe access"
                        )
            except Exception as e:
                logger.error(f"Failed to create thread-safe client: {e}")
                # Fallback to main client (thread-unsafe but functional)
                self._thread_local.client = getattr(self, "client", None)

        return self._thread_local.client

    def list_clusters(
        self, region: Optional[str] = None, **query: Any
    ) -> List[Dict[str, Any]]:
        """
        Retrieve list of Dataproc clusters.

        Args:
            region: Region to filter clusters. If None, search all regions
            **query: Additional query parameters to pass to API

        Returns:
            List of cluster resources

        Raises:
            ValueError: When required parameters are missing
            HttpError: Google Cloud API error
        """
        if not hasattr(self, "client") or not self.client:
            raise ValueError("Client not initialized. Call get_connect() first.")

        cluster_list = []

        if region:
            # Retrieve clusters from specific region
            try:
                request = (
                    self.client.projects()
                    .regions()
                    .clusters()
                    .list(projectId=self.project_id, region=region, **query)
                )
                response = request.execute()
                if "clusters" in response:
                    clusters = response.get("clusters", [])
                    cluster_list.extend(clusters)
                    logger.info(f"Found {len(clusters)} clusters in specified region")
            except HttpError as e:
                if e.resp.status == 404:
                    logger.info("No clusters found in specified region")
                else:
                    logger.error(f"HTTP error listing clusters in region: {e}")
                    raise
            except Exception as e:
                logger.error(f"Failed to list Dataproc clusters in region: {e}")
                raise
        else:
            # Retrieve clusters from all regions (parallel processing)
            cluster_list = self._list_clusters_parallel(**query)

        logger.info(f"Total clusters found: {len(cluster_list)}")
        return cluster_list

    def get_cluster(self, cluster_name: str, region: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific Dataproc cluster information.

        Args:
            cluster_name: Name of the cluster
            region: Region where the cluster is located

        Returns:
            Cluster resource if found, otherwise None

        Raises:
            ValueError: When required parameters are missing
            HttpError: Google Cloud API error (except 404)
        """
        if not cluster_name or not region:
            raise ValueError("cluster_name and region are required")

        if not hasattr(self, "client") or not self.client:
            raise ValueError("Client not initialized. Call get_connect() first.")

        try:
            request = (
                self.client.projects()
                .regions()
                .clusters()
                .get(projectId=self.project_id, region=region, clusterName=cluster_name)
            )
            cluster = request.execute()
            logger.info("Successfully retrieved cluster from region")
            return cluster
        except HttpError as e:
            if e.resp.status == 404:
                logger.info("Cluster not found in specified region")
                return None
            else:
                logger.error(f"HTTP error getting cluster in region: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to get Dataproc cluster in region: {e}")
            return None

    def list_jobs(self, region=None, cluster_name=None, **query):
        """
        Retrieve list of Dataproc jobs.

        Args:
            region (str, optional): Region to filter jobs. If None, search all regions.
            cluster_name (str, optional): Name of cluster to filter jobs.
            **query: Additional query parameters to pass to API.

        Returns:
            list: List of job resources.
        """
        job_list = []

        # Cluster filtering
        if cluster_name:
            query["clusterName"] = cluster_name

        if region:
            try:
                request = (
                    self.client.projects()
                    .regions()
                    .jobs()
                    .list(projectId=self.project_id, region=region, **query)
                )
                response = request.execute()
                if "jobs" in response:
                    job_list.extend(response.get("jobs", []))
            except Exception as e:
                logger.error(f"Failed to list Dataproc jobs in region: {e}")
        else:
            # Retrieve jobs from all regions (parallel processing)
            job_list = self._list_jobs_parallel(**query)

        return job_list

    def list_workflow_templates(self, region=None, **query):
        """
        Retrieve list of Dataproc workflow templates.

        Args:
            region (str, optional): Region to filter templates. If None, search all regions.
            **query: Additional query parameters to pass to API.

        Returns:
            list: List of workflow template resources.
        """
        template_list = []

        if region:
            # Retrieve workflow templates from specific region
            try:
                request = (
                    self.client.projects()
                    .regions()
                    .workflowTemplates()
                    .list(
                        parent=f"projects/{self.project_id}/regions/{region}", **query
                    )
                )
                response = request.execute()
                if "templates" in response:
                    template_list.extend(response.get("templates", []))
            except Exception as e:
                logger.error(
                    f"Failed to list Dataproc workflow templates in region: {e}"
                )
        else:
            # Retrieve workflow templates from all regions
            regions = self._get_available_regions()
            for region_name in regions:
                try:
                    request = (
                        self.client.projects()
                        .regions()
                        .workflowTemplates()
                        .list(
                            parent=f"projects/{self.project_id}/regions/{region_name}",
                            **query,
                        )
                    )
                    response = request.execute()
                    if "templates" in response:
                        template_list.extend(response.get("templates", []))
                except Exception as e:
                    logger.debug(f"No Dataproc workflow templates in region: {e}")
                    continue

        return template_list

    def list_autoscaling_policies(self, region=None, **query):
        """
        Retrieve list of Dataproc autoscaling policies.

        Args:
            region (str, optional): Region to filter policies. If None, search all regions.
            **query: Additional query parameters to pass to API.

        Returns:
            list: List of autoscaling policy resources.
        """
        policy_list = []

        if region:
            # Retrieve autoscaling policies from specific region
            try:
                request = (
                    self.client.projects()
                    .regions()
                    .autoscalingPolicies()
                    .list(
                        parent=f"projects/{self.project_id}/regions/{region}", **query
                    )
                )
                response = request.execute()
                if "policies" in response:
                    policy_list.extend(response.get("policies", []))
            except Exception as e:
                logger.error(
                    f"Failed to list Dataproc autoscaling policies in region: {e}"
                )
        else:
            # Retrieve autoscaling policies from all regions
            regions = self._get_available_regions()
            for region_name in regions:
                try:
                    request = (
                        self.client.projects()
                        .regions()
                        .autoscalingPolicies()
                        .list(
                            parent=f"projects/{self.project_id}/regions/{region_name}",
                            **query,
                        )
                    )
                    response = request.execute()
                    if "policies" in response:
                        policy_list.extend(response.get("policies", []))
                except Exception as e:
                    logger.debug(f"No Dataproc autoscaling policies in region: {e}")
                    continue

        return policy_list

    def _list_clusters_parallel(self, **query) -> List[Dict[str, Any]]:
        """
        Retrieve clusters from all regions through parallel processing.

        Args:
            **query: Additional query parameters to pass to API

        Returns:
            List of clusters found in all regions
        """
        start_time = time.time()
        regions = self._get_optimized_regions()
        cluster_list = []

        # Parallel processing using ThreadPoolExecutor (memory-constrained environment optimization)
        MAX_WORKERS = (
            2  # Optimal setting for stable performance in memory-constrained environments (verified by actual testing)
        )
        max_workers = min(MAX_WORKERS, len(regions))

        # Log parallel processing start
        logger.info(
            f"Starting parallel cluster collection: "
            f"regions={len(regions)}, max_workers={max_workers}, "
            f"global_timeout=90s, individual_timeout=60s (MAX_WORKERS={MAX_WORKERS})"
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create asynchronous tasks for each region
            future_to_region = {
                executor.submit(self._list_clusters_in_region, region, **query): region
                for region in regions
            }

            # Collect completed task results (longer timeout)
            try:
                for future in as_completed(
                    future_to_region, timeout=90
                ):  # 90 second timeout
                    region = future_to_region[future]
                    try:
                        clusters = future.result(timeout=60)  # Individual task 60 second timeout
                        if clusters:
                            cluster_list.extend(clusters)
                            logger.debug(
                                f"Found {len(clusters)} clusters in region {region}"
                            )
                    except Exception as e:
                        logger.debug(f"Error processing region {region}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Timeout waiting for region processing: {e}")

        # Log parallel processing completion
        execution_time = time.time() - start_time
        logger.info(
            f"Parallel cluster collection completed: "
            f"total_clusters={len(cluster_list)}, "
            f"processed_regions={len(regions)}, "
            f"execution_time={execution_time:.2f}s, "
            f"avg_time_per_region={execution_time / len(regions):.2f}s, "
            f"throughput={len(cluster_list) / execution_time:.1f} clusters/sec"
        )

        return cluster_list

    def _list_jobs_parallel(self, **query) -> List[Dict[str, Any]]:
        """
        Retrieve jobs from all regions through parallel processing.

        Args:
            **query: Additional query parameters to pass to API

        Returns:
            List of jobs found in all regions
        """
        start_time = time.time()
        regions = self._get_optimized_regions()
        job_list = []

        # Job collection is less important than clusters, so use fewer workers (memory-constrained environment optimization)
        MAX_JOB_WORKERS = (
            1  # Optimal setting for stable performance in memory-constrained environments (verified by actual testing)
        )
        max_workers = min(MAX_JOB_WORKERS, len(regions))

        # Log parallel processing start
        logger.info(
            f"Starting parallel job collection: "
            f"regions={len(regions)}, max_workers={max_workers}, "
            f"individual_timeout=15s (MAX_JOB_WORKERS={MAX_JOB_WORKERS})"
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_region = {
                executor.submit(self._list_jobs_in_region, region, **query): region
                for region in regions
            }

            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    jobs = future.result(
                        timeout=15
                    )  # 15 second timeout (shorter than clusters)
                    if jobs:
                        job_list.extend(jobs)
                except Exception as e:
                    logger.debug(f"Error processing jobs in region {region}: {e}")
                    continue

        # 병렬 처리 완료 로깅
        execution_time = time.time() - start_time
        logger.info(
            f"Parallel job collection completed: "
            f"total_jobs={len(job_list)}, "
            f"processed_regions={len(regions)}, "
            f"execution_time={execution_time:.2f}s, "
            f"throughput={len(job_list) / max(execution_time, 0.001):.1f} jobs/sec"
        )

        return job_list

    def _list_jobs_in_region(self, region: str, **query) -> List[Dict[str, Any]]:
        """
        Retrieve jobs from specific region (with enhanced error handling).

        Args:
            region: Region name to query
            **query: Additional query parameters to pass to API

        Returns:
            List of jobs in the region
        """
        max_retries = 2  # Jobs are less important than clusters, so reduce retry count
        retry_delay = 1

        for attempt in range(max_retries):
            client = None
            try:
                # Use thread-specific independent client
                client = self._get_thread_safe_client()
                if not client:
                    logger.warning(f"No client available for jobs in region {region}")
                    return []

                request = (
                    client.projects()
                    .regions()
                    .jobs()
                    .list(projectId=self.project_id, region=region, **query)
                )
                response = request.execute()
                return response.get("jobs", [])

            except HttpError as e:
                if e.resp.status in [404, 403]:
                    return []
                elif e.resp.status == 429 and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.debug(f"HTTP error listing jobs in region {region}: {e}")
                    return []

            except (ConnectionError, TimeoutError, socket.timeout, ssl.SSLError) as e:
                if attempt < max_retries - 1:
                    logger.debug(
                        f"Network/SSL error listing jobs in region {region}, retrying: {e}"
                    )
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.debug(
                        f"Network/SSL error listing jobs in region {region}: {e}"
                    )
                    return []

            except Exception as e:
                logger.debug(f"No Dataproc jobs in region {region}: {e}")
                return []

        return []

    def _list_clusters_in_region(self, region: str, **query) -> List[Dict[str, Any]]:
        """
        Retrieve clusters from specific region (with enhanced error handling and thread safety).

        Args:
            region: Region name to query
            **query: Additional query parameters to pass to API

        Returns:
            List of clusters in the region
        """
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            client = None
            try:
                # Use thread-specific independent client
                client = self._get_thread_safe_client()
                if not client:
                    logger.warning(f"No client available for region {region}")
                    return []

                request = (
                    client.projects()
                    .regions()
                    .clusters()
                    .list(projectId=self.project_id, region=region, **query)
                )
                response = request.execute()
                return response.get("clusters", [])

            except HttpError as e:
                if e.resp.status in [404, 403]:
                    # 404: No clusters in region, 403: No access permission
                    return []
                elif e.resp.status == 429:
                    # Rate limit - wait with exponential backoff
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(
                        f"Rate limit in region {region}, waiting {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue
                elif e.resp.status >= 500:
                    # Server error - retry
                    if attempt < max_retries - 1:
                        logger.warning(f"Server error in region {region}, retrying...")
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                else:
                    logger.warning(f"HTTP error in region {region}: {e}")
                    return []

            except (ConnectionError, TimeoutError, socket.timeout) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Network error in region {region}, retrying (attempt {attempt + 1}): {e}"
                    )
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.warning(
                        f"Network error in region {region} after {max_retries} attempts: {e}"
                    )
                    return []

            except ssl.SSLError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"SSL error in region {region}, retrying (attempt {attempt + 1}): {e}"
                    )
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.warning(
                        f"SSL error in region {region} after {max_retries} attempts: {e}"
                    )
                    return []

            except Exception as e:
                # For unexpected errors, just log and return empty list
                logger.debug(f"Unexpected error in region {region}: {e}")
                return []

        return []

    def _get_optimized_regions(self) -> List[str]:
        """
        Return optimized region list.

        When dynamic query fails, improve performance by querying only core regions.

        Returns:
            Optimized region list
        """
        current_time = time.time()

        # Return cached value if cache is valid
        if (
            self._regions_cache is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            return self._regions_cache

        try:
            regions = self._fetch_dataproc_regions()
            logger.info(
                f"Successfully fetched {len(regions)} Dataproc regions dynamically"
            )
        except Exception as e:
            logger.warning(f"Failed to fetch dynamic regions, using core regions: {e}")
            # Use only core regions when dynamic query fails (performance optimization)
            regions = self._get_core_regions()

        # Update cache
        self._regions_cache = regions
        self._cache_timestamp = current_time

        logger.debug(f"Using {len(regions)} regions for Dataproc scanning")
        return regions

    def _get_core_regions(self) -> List[str]:
        """
        Return only core regions to optimize performance.

        Returns:
            List of major usage regions
        """
        return [
            # Major Asia regions
            "asia-east1",  # Taiwan
            "asia-northeast1",  # Tokyo
            "asia-northeast3",  # Seoul
            "asia-southeast1",  # Singapore
            # Major Europe regions
            "europe-west1",  # Belgium
            "europe-west4",  # Netherlands
            # Major US regions
            "us-central1",  # Iowa
            "us-east1",  # South Carolina
            "us-west1",  # Oregon
            "us-west2",  # Los Angeles
        ]

    def _get_available_regions(self) -> List[str]:
        """
        Return list of available Dataproc regions.

        Optimize performance using cache and dynamically query region list.

        Returns:
            List of Google Cloud regions where Dataproc is available
        """
        current_time = time.time()

        # Return cached value if cache is valid
        if (
            self._regions_cache is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            return self._regions_cache

        # Attempt dynamic region query, use fallback on failure
        try:
            regions = self._fetch_dataproc_regions()
            logger.info(
                f"Successfully fetched {len(regions)} Dataproc regions dynamically"
            )
        except Exception as e:
            logger.warning(f"Failed to fetch dynamic regions, using fallback: {e}")
            regions = self._get_fallback_regions()

        # Update cache
        self._regions_cache = regions
        self._cache_timestamp = current_time

        logger.debug(f"Loaded {len(regions)} available regions for Dataproc")
        return regions

    def _fetch_dataproc_regions(self) -> List[str]:
        """
        Dynamically query Dataproc-supported regions through Google Cloud API.

        Returns:
            List of Google Cloud regions that support Dataproc

        Raises:
            Exception: When API call fails
        """
        if not hasattr(self, "client") or not self.client:
            raise ValueError("Client not initialized for dynamic region fetching")

        try:
            # Query available regions through Compute Engine API
            # 부모 클래스의 _build_client 메서드를 사용하여 타임아웃/재시도 설정 적용
            compute_client = self._build_client("compute", "v1")
            request = compute_client.regions().list(project=self.project_id)
            response = request.execute()

            all_regions = []
            if "items" in response:
                for region in response["items"]:
                    region_name = region.get("name", "")
                    # Filter Dataproc-supported regions (generally supported in most regions)
                    if region_name and region.get("status") == "UP":
                        all_regions.append(region_name)

            # Exclude commonly known Dataproc-unsupported regions
            excluded_regions = {"global"}
            supported_regions = [r for r in all_regions if r not in excluded_regions]

            if not supported_regions:
                raise Exception("No supported regions found")

            return sorted(supported_regions)

        except Exception as e:
            logger.error(f"Failed to fetch regions from Compute API: {e}")
            raise

    def _get_fallback_regions(self) -> List[str]:
        """
        Return fallback region list to use when dynamic query fails.

        Returns:
            List of known Dataproc-supported regions
        """
        return [
            "asia-east1",
            "asia-east2",
            "asia-northeast1",
            "asia-northeast2",
            "asia-northeast3",
            "asia-south1",
            "asia-south2",
            "asia-southeast1",
            "asia-southeast2",
            "australia-southeast1",
            "australia-southeast2",
            "europe-north1",
            "europe-west1",
            "europe-west2",
            "europe-west3",
            "europe-west4",
            "europe-west6",
            "europe-central2",
            "northamerica-northeast1",
            "northamerica-northeast2",
            "southamerica-east1",
            "southamerica-west1",
            "us-central1",
            "us-east1",
            "us-east4",
            "us-west1",
            "us-west2",
            "us-west3",
            "us-west4",
        ]
