import logging
import time
from typing import Optional
from core.services.job_manager import JobManager
from core.services.transcription_service import TranscriptionService
from core.services.rag_service import RAGService
from core.services.generation_service import GenerationService
from infra.audio_extractor import AudioExtractor
from infra.visual_processor import VisualProcessingService
from core.domain.models import JobState, JobStatus, FeatureStatus
import os

logger = logging.getLogger(__name__)

class VideoOrchestrator:
    """
    Điều phối viên trung tâm (Orchestrator) sử dụng model Qwen 3.6 Plus
    để quản lý pipeline xử lý video đa phương thức (Audio + Visual).
    """

    def __init__(
        self, 
        job_manager: JobManager,
        audio_extractor: AudioExtractor,
        visual_processor: VisualProcessingService,
        transcription_service: TranscriptionService,
        rag_service: RAGService,
        generation_service: GenerationService
    ):
        self.job_manager = job_manager
        self.audio_extractor = audio_extractor
        self.visual_processor = visual_processor
        self.transcription_service = transcription_service
        self.rag_service = rag_service
        self.generation_service = generation_service

    def run_initial_pipeline(self, job_id: str) -> bool:
        """
        Chạy luồng xử lý đa phương thức: Video -> Audio/Visual -> Transcribe/OCR -> Index -> Qwen Summary.
        """
        try:
            job_state = self.job_manager.get_job_state(job_id)
            if not job_state:
                return False

            job_dir = os.path.dirname(job_state.video_path)
            keyframes_dir = os.path.join(job_dir, "keyframes")

            # 1. Trích xuất Đa phương thức (Audio & Visual)
            self.job_manager.update_status(job_id, JobStatus.EXTRACTING_AUDIO)
            start_time = time.time()
            
            # Tách Audio
            audio_path = job_state.video_path.replace(".mp4", ".wav")
            self.audio_extractor.extract_audio(job_state.video_path, audio_path)
            
            # Tách Keyframes (Slides) - Tính năng mới cho Qwen 3.6 Plus
            logger.info(f"Đang trích xuất Keyframes cho Job {job_id}...")
            keyframes = self.visual_processor.extract_keyframes(job_state.video_path, keyframes_dir)
            
            self.job_manager.update_latency(job_id, "extraction_multi_modal", time.time() - start_time)

            # 2. Dịch âm thanh (Transcription)
            self.job_manager.update_status(job_id, JobStatus.TRANSCRIBING)
            start_time = time.time()
            segments = self.transcription_service.transcribe(audio_path)
            
            if not segments:
                raise Exception("Lỗi khi dịch âm thanh (không có segments).")
            
            self.job_manager.update_latency(job_id, "transcription", time.time() - start_time)

            # 3. Lập chỉ mục RAG (Indexing) - Tích hợp cả keyframes cho visual evidence
            self.job_manager.update_status(job_id, JobStatus.INDEXING)
            start_time = time.time()
            index_path = os.path.join(job_dir, "index")

            # Xây dựng index với keyframes metadata
            if not self.rag_service.build_index_from_segments(segments, index_path, keyframes=keyframes):
                raise Exception("Lỗi khi xây dựng Index.")
            
            self.job_manager.update_latency(job_id, "indexing", time.time() - start_time)

            # 4. Sinh tóm tắt ban đầu & Trích xuất kiến thức (Qwen Map-Reduce)
            self.job_manager.update_status(job_id, JobStatus.GENERATING_SUMMARY)
            start_time = time.time()
            
            context_nodes = self.rag_service.query("Tóm tắt nội dung chi tiết bài giảng", top_k=30)
            summary_output = self.generation_service.generate_summary(context_nodes)
            
            # Lấy các flashcards/quiz đã trích xuất đồng thời
            materials = self.generation_service.get_extracted_materials()
            
            job_state = self.job_manager.get_job_state(job_id)
            job_state.summary = summary_output
            job_state.flashcards = materials["flashcards"]
            job_state.quiz = materials["quiz"]
            
            # Đánh dấu các tính năng đã sẵn sàng ngay lập tức
            job_state.features["summary"] = FeatureStatus.READY
            job_state.features["chat"] = FeatureStatus.READY
            job_state.features["flashcards"] = FeatureStatus.READY
            job_state.features["mini_test"] = FeatureStatus.READY
            
            self.job_manager.save_job_state(job_state)
            
            self.job_manager.update_latency(job_id, "generation_qwen_concurrent", time.time() - start_time)

            # Hoàn tất
            self.job_manager.update_status(job_id, JobStatus.COMPLETED)
            logger.info(f"Job {job_id} hoàn thành với model Qwen 3.6 Plus.")
            return True

        except Exception as e:
            logger.error(f"Pipeline thất bại tại job {job_id}: {str(e)}")
            self.job_manager.update_status(job_id, JobStatus.FAILED, error_message=str(e))
            return False
            
    def generate_on_demand_feature(self, job_id: str, feature: str) -> bool:
        """
        Sinh các tính năng bổ trợ khi có yêu cầu từ người dùng.
        """
        try:
            job_state = self.job_manager.get_job_state(job_id)
            if not job_state: return False
            
            self.job_manager.update_feature_status(job_id, feature, FeatureStatus.PROCESSING)
            
            # Load index nếu chưa có
            index_path = os.path.join(os.path.dirname(job_state.video_path), "index")
            self.rag_service.load_index(index_path)
            
            if feature == "flashcards":
                nodes = self.rag_service.query("Các định nghĩa, công thức và thuật ngữ quan trọng", top_k=15)
                cards = self.generation_service.generate_flashcards(nodes)
                job_state.flashcards = cards
            elif feature == "mini_test":
                nodes = self.rag_service.query("Nội dung quan trọng để kiểm tra kiến thức", top_k=15)
                questions = self.generation_service.generate_quiz(nodes)
                job_state.quiz = questions
            
            job_state.features[feature] = FeatureStatus.READY
            self.job_manager.save_job_state(job_state)
            return True
            
        except Exception as e:
            logger.error(f"Lỗi sinh {feature}: {str(e)}")
            self.job_manager.update_feature_status(job_id, feature, FeatureStatus.FAILED)
            return False
