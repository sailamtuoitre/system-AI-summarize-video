import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

from core.domain.models import FeatureStatus, JobStatus
from core.services.generation_service import GenerationService
from core.services.job_manager import JobManager
from core.services.rag_service import RAGService
from core.services.transcription_service import TranscriptionService
from processing.media_demux import MediaDemuxer
from processing.scene_detector import SceneDetector

logger = logging.getLogger(__name__)


class VideoOrchestrator:
    """
    Dieu phoi pipeline xu ly video.

    Phase 1 flow:
      1. MediaDemuxer (ffmpeg)        -> audio.wav + frames/  (single decode pass)
      2. SceneDetector (PySceneDetect)-> keyframes per scene
      3. TranscriptionService         -> Whisper on full audio (no chunk math)
      4. RAGService                   -> FAISS index (segments + keyframes)
      5. GenerationService            -> summary + flashcards + quiz

    Compared to the old chunked pipeline, this avoids 2-3 redundant decodes
    of the source video and removes the moviepy dependency from the hot path.
    """

    def __init__(
        self,
        job_manager: JobManager,
        media_demuxer: MediaDemuxer,
        scene_detector: SceneDetector,
        transcription_service: TranscriptionService,
        rag_service: RAGService,
        generation_service: GenerationService,
    ):
        self.job_manager = job_manager
        self.media_demuxer = media_demuxer
        self.scene_detector = scene_detector
        self.transcription_service = transcription_service
        self.rag_service = rag_service
        self.generation_service = generation_service

    def run_initial_pipeline(self, job_id: str) -> bool:
        try:
            job_state = self.job_manager.get_job_state(job_id)
            if not job_state:
                return False

            job_dir = os.path.dirname(job_state.video_path)

            # ------------------------------------------------------------------
            # 1. Demux audio + frames (one ffmpeg pass)
            # ------------------------------------------------------------------
            self.job_manager.update_status(job_id, JobStatus.EXTRACTING_AUDIO)
            t0 = time.time()
            demux = self.media_demuxer.run(job_state.video_path, job_dir)
            self.job_manager.update_latency(job_id, "demux", time.time() - t0)

            if demux.audio_path is None:
                logger.warning(
                    "Job %s: video khong co audio, se chi dung visual.", job_id
                )

            # ------------------------------------------------------------------
            # 2 + 3. Scene detection || Transcription  (Phase 2: parallel)
            # ------------------------------------------------------------------
            # Both are CPU-bound but release the GIL (ctranslate2 in faster-whisper,
            # OpenCV/numpy in PySceneDetect), so threads overlap effectively.
            self.job_manager.update_status(job_id, JobStatus.TRANSCRIBING)
            keyframes_dir = os.path.join(job_dir, "keyframes")

            scene_t0 = time.time()
            transcribe_t0 = time.time()
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipe") as pool:
                fut_scenes = pool.submit(
                    self.scene_detector.detect,
                    job_state.video_path,
                    keyframes_dir,
                )
                if demux.audio_path:
                    fut_segments = pool.submit(
                        self.transcription_service.transcribe,
                        demux.audio_path,
                    )
                else:
                    fut_segments = None

                # Resolve scene branch first; record its latency independently.
                try:
                    keyframes = fut_scenes.result()
                except Exception as e:
                    logger.error("Scene detection that bai: %s", e)
                    keyframes = []
                self.job_manager.update_latency(
                    job_id, "scene_detection", time.time() - scene_t0
                )

                # Resolve transcription branch.
                segments: list[dict] = []
                if fut_segments is not None:
                    try:
                        segments = fut_segments.result()
                    except Exception as e:
                        logger.error("Transcription that bai: %s", e)
                        segments = []
                    self.job_manager.update_latency(
                        job_id, "transcription", time.time() - transcribe_t0
                    )

            if not segments:
                logger.warning(
                    "Job %s khong co segments transcript (video khong loi?).",
                    job_id,
                )

            # ------------------------------------------------------------------
            # 4. Build vector index from segments + keyframes
            # ------------------------------------------------------------------
            self.job_manager.update_status(job_id, JobStatus.INDEXING)
            t0 = time.time()
            index_path = os.path.join(job_dir, "index")
            if not self.rag_service.build_index_from_segments(
                segments, index_path, keyframes=keyframes
            ):
                raise Exception("Loi khi xay dung Index.")
            self.job_manager.update_latency(job_id, "indexing", time.time() - t0)

            # ------------------------------------------------------------------
            # 5. Generate summary (and flashcards/quiz inline)
            # ------------------------------------------------------------------
            self.job_manager.update_status(job_id, JobStatus.GENERATING_SUMMARY)
            t0 = time.time()
            context_nodes = self.rag_service.query(
                "Tom tat noi dung chi tiet bai giang", top_k=30
            )
            summary_output = self.generation_service.generate_summary(context_nodes)
            materials = self.generation_service.get_extracted_materials()

            job_state = self.job_manager.get_job_state(job_id)
            if not job_state:
                raise Exception("Khong tim thay job sau khi xu ly xong.")

            job_state.summary = summary_output
            job_state.flashcards = materials["flashcards"]
            job_state.quiz = materials["quiz"]
            job_state.features["summary"] = FeatureStatus.READY
            job_state.features["chat"] = FeatureStatus.READY
            job_state.features["flashcards"] = FeatureStatus.READY
            job_state.features["mini_test"] = FeatureStatus.READY
            self.job_manager.save_job_state(job_state)
            self.job_manager.update_latency(
                job_id, "generation", time.time() - t0
            )

            self.job_manager.update_status(job_id, JobStatus.COMPLETED)
            logger.info("Job %s hoan thanh.", job_id)
            return True

        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            logger.error(
                "[PIPELINE ERROR] tai job %s:\n%s", job_id, error_detail
            )
            self.job_manager.update_status(
                job_id, JobStatus.FAILED, error_message=str(e)
            )
            return False

    def generate_on_demand_feature(self, job_id: str, feature: str) -> bool:
        """Sinh cac tinh nang bo tro khi co yeu cau tu nguoi dung."""
        try:
            job_state = self.job_manager.get_job_state(job_id)
            if not job_state:
                return False

            self.job_manager.update_feature_status(
                job_id, feature, FeatureStatus.PROCESSING
            )

            index_path = os.path.join(
                os.path.dirname(job_state.video_path), "index"
            )
            if not self.rag_service.load_index(index_path):
                raise Exception("Khong the tai index cua job.")

            if feature == "flashcards":
                nodes = self.rag_service.query(
                    "Cac dinh nghia, cong thuc va thuat ngu quan trong",
                    top_k=15,
                )
                cards = self.generation_service.generate_flashcards(nodes)
                if not cards:
                    raise Exception(
                        "Khong tao duoc flashcards tu noi dung video."
                    )
                job_state.flashcards = cards
            elif feature == "mini_test":
                nodes = self.rag_service.query(
                    "Noi dung quan trong de kiem tra kien thuc", top_k=15
                )
                questions = self.generation_service.generate_quiz(nodes)
                if not questions:
                    raise Exception(
                        "Khong tao duoc mini-test tu noi dung video."
                    )
                job_state.quiz = questions

            job_state.features[feature] = FeatureStatus.READY
            self.job_manager.save_job_state(job_state)
            return True

        except Exception as e:
            logger.error("Loi sinh %s: %s", feature, str(e))
            self.job_manager.update_feature_status(
                job_id, feature, FeatureStatus.FAILED
            )
            return False
