import dataclasses
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

from core.domain.models import FeatureStatus, JobStatus
from core.services.checkpoint import Checkpoint
from core.services.generation_service import GenerationService
from core.services.job_manager import JobManager
from core.services.rag_service import RAGService
from core.services.transcription_service import TranscriptionService
from processing.media_demux import DemuxResult, MediaDemuxer, MediaInfo
from processing.scene_detector import SceneDetector
from processing.keyframe_analyzer import KeyframeAnalyzer
from processing.transcript_gate import should_run_visual_stage

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
        keyframe_analyzer: KeyframeAnalyzer | None = None,
    ):
        self.job_manager = job_manager
        self.media_demuxer = media_demuxer
        self.scene_detector = scene_detector
        self.transcription_service = transcription_service
        self.rag_service = rag_service
        self.generation_service = generation_service
        # Optional Phase 4 stage; if None or OCR_ENABLED=false the
        # orchestrator simply skips the analysis step.
        self.keyframe_analyzer = keyframe_analyzer
        self.ocr_enabled = os.getenv("OCR_ENABLED", "false").lower() in (
            "1", "true", "yes", "on",
        )

    def run_initial_pipeline(self, job_id: str) -> bool:
        try:
            job_state = self.job_manager.get_job_state(job_id)
            if not job_state:
                return False

            job_dir = os.path.dirname(job_state.video_path)
            cp = Checkpoint(job_dir)

            # ------------------------------------------------------------------
            # 1. Demux audio + frames (one ffmpeg pass) — resumable
            # ------------------------------------------------------------------
            self.job_manager.update_status(job_id, JobStatus.EXTRACTING_AUDIO)
            cached_demux = cp.load("demux")
            if cached_demux and (
                cached_demux.get("audio_path") is None
                or os.path.exists(cached_demux["audio_path"])
            ):
                # Rehydrate dataclass from JSON without re-running ffmpeg.
                mi = cached_demux.get("media_info") or {}
                demux = DemuxResult(
                    audio_path=cached_demux.get("audio_path"),
                    frames_dir=cached_demux.get("frames_dir", ""),
                    frame_paths=cached_demux.get("frame_paths", []),
                    media_info=MediaInfo(**mi) if mi else MediaInfo(
                        duration=0.0, fps=0.0, width=0, height=0,
                        has_audio=False, video_codec=None, audio_codec=None,
                    ),
                )
            else:
                t0 = time.time()
                demux = self.media_demuxer.run(job_state.video_path, job_dir)
                self.job_manager.update_latency(job_id, "demux", time.time() - t0)
                cp.save("demux", dataclasses.asdict(demux))

            if demux.audio_path is None:
                logger.warning(
                    "Job %s: video khong co audio, se chi dung visual.", job_id
                )

            # ------------------------------------------------------------------
            # 2 + 3. Scene detection || Transcription  (Phase 2: parallel)
            #         each independently resumable from its own checkpoint
            # ------------------------------------------------------------------
            self.job_manager.update_status(job_id, JobStatus.TRANSCRIBING)
            keyframes_dir = os.path.join(job_dir, "keyframes")

            cached_scenes = cp.load("scenes")
            cached_segments = cp.load("segments")

            need_scenes = cached_scenes is None
            need_transcribe = cached_segments is None and demux.audio_path is not None

            keyframes: list[dict] = cached_scenes or []
            segments: list[dict] = cached_segments or []

            if need_scenes or need_transcribe:
                scene_t0 = time.time()
                transcribe_t0 = time.time()
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipe") as pool:
                    fut_scenes = (
                        pool.submit(
                            self.scene_detector.detect,
                            job_state.video_path,
                            keyframes_dir,
                        )
                        if need_scenes
                        else None
                    )
                    fut_segments = (
                        pool.submit(
                            self.transcription_service.transcribe,
                            demux.audio_path,
                        )
                        if need_transcribe
                        else None
                    )

                    if fut_scenes is not None:
                        try:
                            keyframes = fut_scenes.result()
                        except Exception as e:
                            logger.error("Scene detection that bai: %s", e)
                            keyframes = []
                        self.job_manager.update_latency(
                            job_id, "scene_detection", time.time() - scene_t0
                        )
                        cp.save("scenes", keyframes)

                    if fut_segments is not None:
                        try:
                            segments = fut_segments.result()
                        except Exception as e:
                            logger.error("Transcription that bai: %s", e)
                            segments = []
                        self.job_manager.update_latency(
                            job_id, "transcription", time.time() - transcribe_t0
                        )
                        cp.save("segments", segments)

            if not segments:
                logger.warning(
                    "Job %s khong co segments transcript (video khong loi?).",
                    job_id,
                )

            # ------------------------------------------------------------------
            # 3.5. Keyframe analysis cascade (PaddleOCR -> Qwen-VL fallback)
            # ------------------------------------------------------------------
            # Optional Phase 4 stage. Adds `ocr_text` and `caption` to each
            # keyframe so the RAG layer can index slide content alongside
            # transcripts. Skipped silently when disabled OR when Stage T
            # judges the transcript to be a talk-head with no deixis cues.
            if (
                self.ocr_enabled
                and self.keyframe_analyzer is not None
                and keyframes
            ):
                cached_kf4 = cp.load("keyframes_phase4")
                if cached_kf4 is not None:
                    keyframes = cached_kf4
                else:
                    # Stage T — gate Phase 4 on transcript content. Always runs
                    # Phase 4 if transcript is empty (silent video / slide deck).
                    run_visual, hits = should_run_visual_stage(segments)
                    if not run_visual:
                        logger.info(
                            "Job %s: Stage T skip Phase 4 (deixis_hits=%d).",
                            job_id, hits,
                        )
                    else:
                        analyze_t0 = time.time()
                        try:
                            keyframes = self.keyframe_analyzer.analyze(keyframes)
                        except Exception as e:
                            logger.warning(
                                "KeyframeAnalyzer that bai: %s. Tiep tuc khong co OCR.", e
                            )
                        self.job_manager.update_latency(
                            job_id, "keyframe_analysis", time.time() - analyze_t0
                        )
                    cp.save("keyframes_phase4", keyframes)

            # ------------------------------------------------------------------
            # 4. Build vector index from segments + keyframes — resumable
            # ------------------------------------------------------------------
            self.job_manager.update_status(job_id, JobStatus.INDEXING)
            index_path = os.path.join(job_dir, "index")
            if cp.has_index() and self.rag_service.load_index(index_path):
                logger.info("Job %s: index reused tu disk, bo qua build.", job_id)
            else:
                t0 = time.time()
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
