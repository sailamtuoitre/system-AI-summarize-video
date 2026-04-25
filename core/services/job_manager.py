import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from core.domain.models import JobState, JobStatus, FeatureStatus


class JobManager:
    """
    Service dieu phoi va quan ly trang thai cua cac tien trinh xu ly video.
    Dam bao viec luu tru, cap nhat va truy xuat trang thai Job nhat quan.
    """

    def __init__(self, base_data_dir: str = "./data/jobs"):
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

    def _get_job_dir(self, job_id: str) -> Path:
        return self.base_data_dir / job_id

    def _get_state_file_path(self, job_id: str) -> Path:
        return self._get_job_dir(job_id) / "job_state.json"

    def create_job(self, video_filename: str) -> JobState:
        job_id = str(uuid.uuid4())
        job_dir = self._get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        video_path = str(job_dir / "video.mp4")

        job_state = JobState(
            job_id=job_id,
            video_path=video_path,
            filename=video_filename,
            status=JobStatus.PENDING,
        )

        self.save_job_state(job_state)
        return job_state

    def save_job_state(self, job_state: JobState) -> None:
        file_path = self._get_state_file_path(job_state.job_id)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temp file first so interrupted writes do not leave empty JSON behind.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=file_path.parent,
            delete=False,
            suffix=".tmp",
        ) as temp_file:
            temp_file.write(job_state.model_dump_json(indent=4, ensure_ascii=False))
            temp_path = Path(temp_file.name)

        temp_path.replace(file_path)

    def get_job_state(self, job_id: str) -> Optional[JobState]:
        file_path = self._get_state_file_path(job_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return JobState(**data)
        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def list_all_jobs(self) -> List[JobState]:
        jobs: List[JobState] = []
        if not self.base_data_dir.exists():
            return jobs

        for job_dir in self.base_data_dir.iterdir():
            if job_dir.is_dir():
                job_state = self.get_job_state(job_dir.name)
                if job_state:
                    jobs.append(job_state)

        return sorted(jobs, key=lambda x: x.created_at, reverse=True)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
    ) -> Optional[JobState]:
        job_state = self.get_job_state(job_id)
        if not job_state:
            return None

        job_state.status = status
        if error_message:
            job_state.error_message = error_message

        if status == JobStatus.COMPLETED:
            job_state.completed_at = datetime.now()

        self.save_job_state(job_state)
        return job_state

    def update_latency(self, job_id: str, stage: str, duration: float) -> Optional[JobState]:
        job_state = self.get_job_state(job_id)
        if not job_state:
            return None

        job_state.latency[stage] = duration
        self.save_job_state(job_state)
        return job_state

    def update_feature_status(
        self,
        job_id: str,
        feature_name: str,
        status: FeatureStatus,
    ) -> Optional[JobState]:
        job_state = self.get_job_state(job_id)
        if not job_state:
            return None

        if feature_name in job_state.features:
            job_state.features[feature_name] = status
            self.save_job_state(job_state)

        return job_state

    def update_chunk_progress(
        self,
        job_id: str,
        *,
        total_chunks: Optional[int] = None,
        processed_chunks: Optional[int] = None,
        chunk_duration_seconds: Optional[int] = None,
    ) -> Optional[JobState]:
        job_state = self.get_job_state(job_id)
        if not job_state:
            return None

        if chunk_duration_seconds is not None:
            job_state.chunk_progress.chunk_duration_seconds = chunk_duration_seconds
        if total_chunks is not None:
            job_state.chunk_progress.total_chunks = total_chunks
        if processed_chunks is not None:
            job_state.chunk_progress.processed_chunks = processed_chunks

        self.save_job_state(job_state)
        return job_state
