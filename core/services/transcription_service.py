import logging
from typing import List, Dict, Any, Optional
from faster_whisper import WhisperModel
import time

logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Dịch vụ chuyển đổi giọng nói thành văn bản sử dụng faster-whisper.
    """

    def __init__(self, model_size: str = "medium", device: str = "cpu", compute_type: str = "int8"):
        """
        Khởi tạo TranscriptionService.
        
        Args:
            model_size (str): Kích thước mô hình (tiny, base, small, medium, large-v3).
            device (str): Thiết bị chạy (cpu, cuda).
            compute_type (str): Kiểu tính toán (int8, float16).
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        """Tải mô hình vào bộ nhớ chỉ khi cần (lazy loading)."""
        if self._model is None:
            logger.info(f"Đang tải mô hình Whisper ({self.model_size}) trên {self.device}...")
            self._model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
            logger.info("Mô hình Whisper đã sẵn sàng.")

    def transcribe(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Thực hiện chuyển đổi âm thanh thành văn bản có mốc thời gian.
        
        Args:
            audio_path (str): Đường dẫn file âm thanh (.wav).
            
        Returns:
            List[Dict[str, Any]]: Danh sách các segments văn bản.
        """
        self._load_model()
        
        logger.info(f"Bắt đầu dịch âm thanh từ {audio_path}...")
        start_time = time.time()
        
        try:
            # beam_size=5 cho độ chính xác tốt, word_timestamps=False (chúng ta chỉ cần segment)
            segments, info = self._model.transcribe(
                audio_path, 
                beam_size=5,
                vad_filter=True, # Lọc các đoạn im lặng để nhanh hơn
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            output_segments = []
            for segment in segments:
                output_segments.append({
                    "id": segment.id,
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "confidence": round(segment.avg_logprob, 4)
                })
            
            duration = time.time() - start_time
            logger.info(f"Dịch âm thanh hoàn tất trong {duration:.2f} giây. Tổng cộng {len(output_segments)} segments.")
            return output_segments

        except Exception as e:
            logger.error(f"Lỗi trong quá trình dịch âm thanh: {str(e)}")
            return []
