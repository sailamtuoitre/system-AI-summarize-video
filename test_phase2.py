"""
Phase 2 isolated end-to-end test.

Exercises:
  1. MediaDemuxer (ffmpeg) -> audio.wav + frames/
  2. SceneDetector || TranscriptionService (Phase 2 parallel branch)
  3. RAGService.build_index_from_segments

Skips the LLM Map-Reduce stage so it can run without 9router. Verifies the
Phase 2 parallelism by comparing wall-clock(stage 2) to sum(scene_time, whisper_time).
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("phase2_test")


def main(video_path: str, keep: bool = False) -> int:
    if not os.path.exists(video_path):
        log.error("Video khong ton tai: %s", video_path)
        return 2

    from processing.media_demux import MediaDemuxer
    from processing.scene_detector import SceneDetector
    from core.services.transcription_service import TranscriptionService
    from core.services.rag_service import RAGService

    work = Path(tempfile.mkdtemp(prefix="phase2_"))
    log.info("Workdir: %s", work)
    try:
        # ---------------------------------------------------------------- 1. Demux
        demuxer = MediaDemuxer(audio_sample_rate=16000, frame_fps=1.0)
        t0 = time.time()
        demux = demuxer.run(video_path, str(work))
        demux_t = time.time() - t0
        log.info("[STAGE 1] demux: %.2fs (audio=%s, frames=%d)",
                 demux_t, demux.audio_path, len(demux.frame_paths))

        if demux.audio_path is None:
            log.error("Video khong co audio -> khong test duoc parallel branch.")
            return 3

        # ---------------------------------------------------------------- 2. Parallel branches
        scene_detector = SceneDetector(threshold=27.0, min_scene_len=1.5)
        transcription = TranscriptionService(model_size=os.getenv("WHISPER_MODEL_SIZE", "small"))

        keyframes_dir = str(work / "keyframes")

        wall_t0 = time.time()
        scene_t = whisper_t = 0.0
        scene_t0 = whisper_t0 = wall_t0
        keyframes: list = []
        segments: list = []
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipe") as pool:
            fut_scenes = pool.submit(scene_detector.detect, video_path, keyframes_dir)
            fut_segments = pool.submit(transcription.transcribe, demux.audio_path)

            try:
                keyframes = fut_scenes.result()
            except Exception as e:
                log.error("Scene detection failed: %s", e)
            scene_t = time.time() - scene_t0

            try:
                segments = fut_segments.result()
            except Exception as e:
                log.error("Transcription failed: %s", e)
            whisper_t = time.time() - whisper_t0

        wall_t = time.time() - wall_t0
        log.info("[STAGE 2 parallel] wall=%.2fs  scene=%.2fs  whisper=%.2fs  serial-equiv=%.2fs",
                 wall_t, scene_t, whisper_t, scene_t + whisper_t)
        log.info("  -> scenes=%d, segments=%d", len(keyframes), len(segments))

        speedup = (scene_t + whisper_t) / wall_t if wall_t > 0 else 0
        overlap_pct = (1 - wall_t / (scene_t + whisper_t)) * 100 if (scene_t + whisper_t) > 0 else 0
        log.info("  -> speedup vs serial = %.2fx, overlap = %.1f%%", speedup, overlap_pct)

        # ---------------------------------------------------------------- 3. Index
        rag = RAGService()
        index_path = str(work / "index")
        t0 = time.time()
        ok = rag.build_index_from_segments(segments, index_path, keyframes=keyframes)
        index_t = time.time() - t0
        log.info("[STAGE 3] indexing: %.2fs (ok=%s)", index_t, ok)
        if not ok:
            log.error("build_index_from_segments returned False.")
            return 4

        # ---------------------------------------------------------------- 4. Smoke retrieval (no LLM)
        nodes = rag.query("noi dung chinh", top_k=3)
        log.info("[STAGE 4] retrieval smoke: top_k=3 -> got %d nodes", len(nodes))
        for i, n in enumerate(nodes):
            log.info("    node %d  score=%.3f  text=%r", i,
                     n.get("score") or 0.0, (n.get("text") or "")[:80])

        # ---------------------------------------------------------------- Summary
        total = demux_t + wall_t + index_t
        print()
        print("=" * 60)
        print("Phase 2 isolated test PASSED")
        print("=" * 60)
        print(f"  demux                 : {demux_t:7.2f} s")
        print(f"  scene||whisper (wall) : {wall_t:7.2f} s")
        print(f"      scene branch      : {scene_t:7.2f} s")
        print(f"      whisper branch    : {whisper_t:7.2f} s")
        print(f"      serial-equiv      : {scene_t + whisper_t:7.2f} s")
        print(f"      speedup           : {speedup:7.2f}x")
        print(f"      overlap           : {overlap_pct:7.1f} %")
        print(f"  indexing              : {index_t:7.2f} s")
        print(f"  TOTAL (no LLM)        : {total:7.2f} s")
        print("=" * 60)
        return 0
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)
        else:
            log.info("Workdir kept at %s", work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 isolated test")
    parser.add_argument("video", nargs="?",
                        help="Path to a .mp4. If omitted, uses an existing job video.")
    parser.add_argument("--keep", action="store_true", help="Keep workdir after run")
    args = parser.parse_args()

    video = args.video
    if not video:
        # Pick an existing job video (smallest non-trivial)
        candidates = sorted(
            Path("data/jobs").glob("*/video.mp4"),
            key=lambda p: p.stat().st_size,
        )
        candidates = [p for p in candidates if p.stat().st_size > 100_000]
        if not candidates:
            print("Khong tim thay video test trong data/jobs.", file=sys.stderr)
            sys.exit(2)
        video = str(candidates[0])
        print(f"Auto-selected: {video} ({candidates[0].stat().st_size} bytes)")

    sys.exit(main(video, keep=args.keep))
