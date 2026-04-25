import logging
import os
from typing import List, Dict, Any, Optional
from faster_whisper import WhisperModel
import time

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Phase 3 — Whisper tuning knobs (env-tunable)
# --------------------------------------------------------------------------- #
# beam_size=1 is ~2x faster than beam_size=5 with ~1% WER loss. Acceptable for
# a learning/summarisation use case. Bump to 3-5 only if accuracy drops.
WHISPER_BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
# Tighter VAD trims more silence -> less audio for Whisper to process.
WHISPER_VAD_MIN_SILENCE_MS = int(os.getenv("WHISPER_VAD_MIN_SILENCE_MS", "300"))
WHISPER_VAD_THRESHOLD = float(os.getenv("WHISPER_VAD_THRESHOLD", "0.45"))
# 0 = let ctranslate2 decide (= os.cpu_count()). num_workers>1 enables internal
# pipeline parallelism for chunked decoding.
WHISPER_CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "0"))
WHISPER_NUM_WORKERS = int(os.getenv("WHISPER_NUM_WORKERS", "2"))
# Pin language to skip auto-detect (saves ~1-3s per file). Empty = auto.
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "").strip() or None
# Drop segments below this avg_logprob (very low-confidence = usually
# hallucinated noise). Set to None / negative to disable.
WHISPER_MIN_CONFIDENCE = float(os.getenv("WHISPER_MIN_CONFIDENCE", "-1.0"))


class TranscriptionService:
    """
    Dịch vụ chuyển đổi giọng nói thành văn bản sử dụng faster-whisper.
    Phase 3: tuned beam_size, VAD, threading, language pinning, confidence filter.
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
            logger.info(
                "Đang tải mô hình Whisper (%s) trên %s [threads=%d, workers=%d]...",
                self.model_size, self.device,
                WHISPER_CPU_THREADS, WHISPER_NUM_WORKERS,
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=WHISPER_CPU_THREADS,
                num_workers=WHISPER_NUM_WORKERS,
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

        logger.info(
            "Bắt đầu dịch âm thanh từ %s [beam=%d, vad_silence=%dms, lang=%s]...",
            audio_path, WHISPER_BEAM_SIZE, WHISPER_VAD_MIN_SILENCE_MS,
            WHISPER_LANGUAGE or "auto",
        )
        start_time = time.time()

        try:
            segments, info = self._model.transcribe(
                audio_path,
                beam_size=WHISPER_BEAM_SIZE,
                language=WHISPER_LANGUAGE,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=WHISPER_VAD_MIN_SILENCE_MS,
                    threshold=WHISPER_VAD_THRESHOLD,
                ),
                condition_on_previous_text=False,  # reduces hallucination loops
            )
            
            output_segments = []
            dropped_low_conf = 0
            for segment in segments:
                text = segment.text.strip()
                if not text:
                    continue
                # Phase 3: confidence filter — drop noisy hallucinations
                if (
                    WHISPER_MIN_CONFIDENCE > -1.0
                    and segment.avg_logprob is not None
                    and segment.avg_logprob < WHISPER_MIN_CONFIDENCE
                ):
                    dropped_low_conf += 1
                    continue
                output_segments.append({
                    "id": segment.id,
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": text,
                    "confidence": round(segment.avg_logprob, 4) if segment.avg_logprob is not None else 0.0,
                })

            duration = time.time() - start_time
            logger.info(
                "Dịch âm thanh hoàn tất trong %.2fs. Segments=%d (dropped_low_conf=%d, lang=%s, prob=%.2f).",
                duration, len(output_segments), dropped_low_conf,
                getattr(info, "language", "?"),
                getattr(info, "language_probability", 0.0) or 0.0,
            )
            return output_segments

        except Exception as e:
            logger.error(f"Lỗi trong quá trình dịch âm thanh: {str(e)}")
            return []
