import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.domain.models import JobState, JobStatus, FeatureStatus

class JobManager:
    """
    Service điều phối và quản lý trạng thái của các tiến trình xử lý video.
    Đảm bảo việc lưu trữ, cập nhật và truy xuất trạng thái Job (job_state.json) nhất quán.
    """

    def __init__(self, base_data_dir: str = "./data/jobs"):
        """
        Khởi tạo JobManager.
        
        Args:
            base_data_dir (str): Đường dẫn thư mục gốc lưu trữ dữ liệu các jobs.
        """
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

    def _get_job_dir(self, job_id: str) -> Path:
        """Lấy đường dẫn thư mục của một job cụ thể."""
        return self.base_data_dir / job_id

    def _get_state_file_path(self, job_id: str) -> Path:
        """Lấy đường dẫn file job_state.json."""
        return self._get_job_dir(job_id) / "job_state.json"

    def create_job(self, video_filename: str) -> JobState:
        """
        Khởi tạo một Job mới.
        
        Args:
            video_filename (str): Tên file video gốc.
            
        Returns:
            JobState: Đối tượng trạng thái job vừa khởi tạo.
        """
        job_id = str(uuid.uuid4())
        job_dir = self._get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        video_path = str(job_dir / "video.mp4")
        
        job_state = JobState(
            job_id=job_id,
            video_path=video_path,
            status=JobStatus.PENDING
        )
        
        self.save_job_state(job_state)
        return job_state

    def save_job_state(self, job_state: JobState) -> None:
        """
        Lưu trạng thái Job vào file job_state.json.
        
        Args:
            job_state (JobState): Đối tượng trạng thái job cần lưu.
        """
        file_path = self._get_state_file_path(job_state.job_id)
        with open(file_path, "w", encoding="utf-8") as f:
            # Chuyển đổi pydantic model sang dict/json
            f.write(job_state.json(indent=4, ensure_ascii=False))

    def get_job_state(self, job_id: str) -> Optional[JobState]:
        """
        Truy xuất trạng thái của một Job.
        
        Args:
            job_id (str): ID của job cần truy vấn.
            
        Returns:
            Optional[JobState]: Đối tượng trạng thái job hoặc None nếu không tồn tại.
        """
        file_path = self._get_state_file_path(job_id)
        if not file_path.exists():
            return None
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return JobState(**data)

    def list_all_jobs(self) -> List[JobState]:
        """
        Lấy danh sách tất cả các Job hiện có.
        """
        jobs = []
        if not self.base_data_dir.exists():
            return jobs
            
        for job_dir in self.base_data_dir.iterdir():
            if job_dir.is_dir():
                job_state = self.get_job_state(job_dir.name)
                if job_state:
                    jobs.append(job_state)
        
        # Sắp xếp theo thời gian khởi tạo (giả định folder name hoặc meta)
        return sorted(jobs, key=lambda x: x.job_id, reverse=True)

    def update_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None) -> Optional[JobState]:
        """
        Cập nhật trạng thái xử lý của Job.
        
        Args:
            job_id (str): ID của job.
            status (JobStatus): Trạng thái mới.
            error_message (Optional[str]): Thông báo lỗi nếu có.
            
        Returns:
            Optional[JobState]: Trạng thái job sau khi cập nhật.
        """
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
        """
        Ghi lại thời gian xử lý của một giai đoạn.
        
        Args:
            job_id (str): ID của job.
            stage (str): Tên giai đoạn (ví dụ: 'transcription').
            duration (float): Thời gian thực hiện tính bằng giây.
            
        Returns:
            Optional[JobState]: Trạng thái job sau khi cập nhật.
        """
        job_state = self.get_job_state(job_id)
        if not job_state:
            return None
            
        job_state.latency[stage] = duration
        self.save_job_state(job_state)
        return job_state

    def update_feature_status(self, job_id: str, feature_name: str, status: FeatureStatus) -> Optional[JobState]:
        """
        Cập nhật trạng thái của các tính năng On-demand (Flashcards, Mini-test).
        
        Args:
            job_id (str): ID của job.
            feature_name (str): Tên tính năng ('flashcards', 'mini_test').
            status (FeatureStatus): Trạng thái mới.
            
        Returns:
            Optional[JobState]: Trạng thái job sau khi cập nhật.
        """
        job_state = self.get_job_state(job_id)
        if not job_state:
            return None
            
        if feature_name in job_state.features:
            job_state.features[feature_name] = status
            self.save_job_state(job_state)
            
        return job_state
