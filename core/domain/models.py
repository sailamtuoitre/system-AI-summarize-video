from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class JobStatus(str, Enum):
    """Trạng thái hiện tại của một tiến trình xử lý video."""
    PENDING = "pending"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    INDEXING = "indexing"
    GENERATING_SUMMARY = "generating_summary"
    COMPLETED = "completed"
    FAILED = "failed"

class FeatureStatus(str, Enum):
    """Trạng thái của các tính năng phụ trợ (On-demand)."""
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class Evidence(BaseModel):
    """Mô tả bằng chứng trích dẫn từ video."""
    timestamp: str = Field(..., description="Mốc thời gian mm:ss")
    quote: str = Field(..., description="Đoạn trích dẫn nguyên văn từ transcript")
    source_node_id: str = Field(..., description="ID của node trong LlamaIndex để đối soát")

class SummaryOutput(BaseModel):
    """Cấu trúc dữ liệu cho tóm tắt video."""
    initial_summary: str = Field(..., description="Đoạn văn tóm tắt tổng quan nội dung")

class Flashcard(BaseModel):
    """Cấu trúc dữ liệu cho một thẻ ghi nhớ."""
    front: str = Field(..., description="Câu hỏi hoặc thuật ngữ")
    back: str = Field(..., description="Giải thích chi tiết")
    latex: Optional[str] = Field(None, description="Công thức toán học nếu có")
    evidence: Evidence

class QuizQuestion(BaseModel):
    """Cấu trúc dữ liệu cho một câu hỏi trắc nghiệm."""
    question: str = Field(..., description="Nội dung câu hỏi")
    options: List[str] = Field(..., min_items=4, max_items=4, description="Danh sách 4 lựa chọn A, B, C, D")
    answer: str = Field(..., description="Đáp án đúng")
    explanation: str = Field(..., description="Giải thích chi tiết lý do chọn đáp án")
    evidence: Evidence

class JobState(BaseModel):
    """Trạng thái tổng thể và quản lý dữ liệu của một Job xử lý."""
    job_id: str
    video_path: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Trạng thái các tính năng phụ
    features: Dict[str, FeatureStatus] = {
        "summary": FeatureStatus.NOT_STARTED,
        "chat": FeatureStatus.NOT_STARTED,
        "flashcards": FeatureStatus.NOT_STARTED,
        "mini_test": FeatureStatus.NOT_STARTED
    }
    
    # Kết quả xử lý
    summary: Optional[SummaryOutput] = None
    flashcards: List[Flashcard] = []
    quiz: List[QuizQuestion] = []
    
    # Log hiệu suất
    latency: Dict[str, float] = {}
    error_message: Optional[str] = None

    class Config:
        use_enum_values = True
