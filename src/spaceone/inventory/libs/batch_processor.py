import logging
from typing import Dict, List

_LOGGER = logging.getLogger(__name__)


class BatchJobProcessor:
    """
    Reusable helper class for Batch Job processing.

    This class handles complex Batch Job data processing logic
    and is designed to be reusable across different modules.
    """

    def __init__(self, batch_connector):
        """
        Args:
            batch_connector: Batch API connector instance
        """
        self.batch_connector = batch_connector

    def process_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Process Jobs data efficiently.

        Args:
            jobs: List of Jobs to process

        Returns:
            List[Dict]: Processed Job list
        """
        processed_jobs = []

        for job in jobs:
            try:
                processed_job = self._process_single_job(job)
                processed_jobs.append(processed_job)
            except Exception as e:
                job_name = job.get("name", "unknown")
                _LOGGER.error(f"Failed to process job {job_name}: {e}", exc_info=True)
                processed_jobs.append(self._create_basic_job_data(job))

        return processed_jobs

    def _process_single_job(self, job: Dict) -> Dict:
        """
        Process individual Job.

        Args:
            job: Job data to process

        Returns:
            Dict: Processed Job data
        """
        job_name = job.get("name", "")
        task_groups_raw = job.get("taskGroups", [])

        if len(task_groups_raw) == 0:
            job_spec = job.get("spec", {})
            if job_spec:
                task_groups_raw = job_spec.get("taskGroups", [])

            if len(task_groups_raw) == 0:
                try:
                    detailed_job = self.batch_connector.get_job_details(job_name)
                    if detailed_job:
                        detailed_spec = detailed_job.get("spec", {})
                        if detailed_spec:
                            task_groups_raw = detailed_spec.get("taskGroups", [])

                        if len(task_groups_raw) == 0:
                            task_groups_raw = detailed_job.get("taskGroups", [])
                except Exception as e:
                    _LOGGER.warning(
                        f"Failed to get detailed job info for {job_name}: {e}"
                    )

        task_groups = self._process_task_groups(
            task_groups_raw, job.get("allocationPolicy", {}), job_name
        )

        return {
            "name": job_name,
            "uid": job.get("uid", ""),
            "display_name": job.get("displayName", ""),
            "state": job.get("status", {}).get("state", ""),
            "create_time": job.get("createTime", ""),
            "update_time": job.get("updateTime", ""),
            "task_groups": task_groups,
        }

    def _process_task_groups(
        self, task_groups_raw: List[Dict], allocation_policy: Dict, job_name: str
    ) -> List[Dict]:
        """
        Process TaskGroups efficiently.

        Args:
            task_groups_raw: Original TaskGroup list
            allocation_policy: Allocation policy
            job_name: Full path name of the Job

        Returns:
            List[Dict]: Processed TaskGroup list
        """
        instances = allocation_policy.get("instances", [])
        machine_type = ""
        if instances and instances[0].get("policy"):
            machine_type = instances[0]["policy"].get("machineType", "")

        processed_groups = []
        for task_group in task_groups_raw:
            try:
                processed_group = self._process_single_task_group(
                    task_group, machine_type, job_name
                )
                processed_groups.append(processed_group)
            except Exception as e:
                group_name = task_group.get("name", "unknown")
                _LOGGER.error(
                    f"Failed to process task group {group_name}: {e}", exc_info=True
                )
                processed_groups.append(self._create_basic_task_group_data(task_group))

        return processed_groups

    def _process_single_task_group(
        self, task_group: Dict, machine_type: str, job_name: str
    ) -> Dict:
        """
        Process individual TaskGroup.

        Args:
            task_group: TaskGroup data
            machine_type: Machine type
            job_name: Full path name of the Job

        Returns:
            Dict: Processed TaskGroup data
        """
        task_spec = task_group.get("taskSpec", {})
        runnables = task_spec.get("runnables", [])

        image_uri = ""
        if runnables and runnables[0].get("container"):
            image_uri = runnables[0]["container"].get("imageUri", "")

        compute_resource = task_spec.get("computeResource", {})

        task_group_name = task_group.get("name", "")

        if task_group_name and task_group_name.startswith("projects/"):
            full_task_group_path = task_group_name
        else:
            full_task_group_path = (
                f"{job_name}/taskGroups/{task_group_name}" if task_group_name else ""
            )

        tasks = self._collect_tasks_safe(full_task_group_path)

        return {
            "name": task_group_name,
            "task_count": task_group.get("taskCount", "0"),
            "parallelism": task_group.get("parallelism", ""),
            "machine_type": machine_type,
            "image_uri": image_uri,
            "cpu_milli": compute_resource.get("cpuMilli", ""),
            "memory_mib": compute_resource.get("memoryMib", ""),
            "tasks": tasks,
        }

    def _collect_tasks_safe(self, task_group_name: str) -> List[Dict]:
        """
        Safely collect Tasks.

        Args:
            task_group_name: TaskGroup name

        Returns:
            List[Dict]: Task list
        """
        if not task_group_name:
            return []

        try:
            tasks = self.batch_connector.list_tasks(task_group_name)
            processed_tasks = []
            for task in tasks:
                status_events = task.get("status", {}).get("statusEvents", [])

                last_event_type = ""
                last_event_time = ""
                if status_events:
                    sorted_events = sorted(
                        status_events,
                        key=lambda x: x.get("eventTime", ""),
                        reverse=True,
                    )
                    latest_event = sorted_events[0]
                    last_event_type = latest_event.get("type", "")
                    last_event_time = latest_event.get("eventTime", "")

                processed_tasks.append(
                    {
                        "name": task.get("name", ""),
                        "state": task.get("status", {}).get("state", ""),
                        "status_events": status_events,
                        "last_event_type": last_event_type,
                        "last_event_time": last_event_time,
                    }
                )

            return processed_tasks
        except Exception as e:
            _LOGGER.error(
                f"Failed to collect tasks for {task_group_name}: {e}", exc_info=True
            )
            return []

    def _create_basic_job_data(self, job: Dict) -> Dict:
        """
        Create basic Job data.

        Args:
            job: Original Job data

        Returns:
            Dict: Basic Job data
        """
        return {
            "name": job.get("name", ""),
            "uid": job.get("uid", ""),
            "display_name": job.get("displayName", ""),
            "state": job.get("status", {}).get("state", "UNKNOWN"),
            "create_time": job.get("createTime", ""),
            "update_time": job.get("updateTime", ""),
            "task_groups": [],
        }

    def _create_basic_task_group_data(self, task_group: Dict) -> Dict:
        """
        Create basic TaskGroup data.

        Args:
            task_group: Original TaskGroup data

        Returns:
            Dict: Basic TaskGroup data
        """
        return {
            "name": task_group.get("name", ""),
            "task_count": task_group.get("taskCount", "0"),
            "parallelism": task_group.get("parallelism", ""),
            "machine_type": "",
            "image_uri": "",
            "cpu_milli": "",
            "memory_mib": "",
            "tasks": [],
        }
