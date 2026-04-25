"""
Scene-based keyframe extraction using PySceneDetect.

Replaces the per-second pixel-diff loop in `visual_processor.py`. PySceneDetect
adaptively samples the video and detects true scene boundaries (slide changes,
hard cuts), which is faster and produces cleaner keyframes for OCR/RAG.

For each detected scene we save one representative frame (taken at the scene
midpoint) as JPEG. If no scenes are detected (very static video), the whole
video is treated as a single scene and one keyframe is saved at t = 0.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def _format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


class SceneDetector:
    """
    Detect scenes and save one representative keyframe per scene.

    Args:
        threshold: ContentDetector threshold. Lower = more sensitive (more
                   scenes). Default 27 works well for slide videos; use ~15
                   for vlogs/demos with subtle cuts.
        min_scene_len: minimum scene length in seconds; suppresses flicker.
    """

    def __init__(self, threshold: float = 27.0, min_scene_len: float = 1.5):
        self.threshold = threshold
        self.min_scene_len = min_scene_len

    def detect(self, video_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """
        Run scene detection and save keyframes.

        Returns:
            list of {
              "scene_index": int,
              "start": float,        # seconds
              "end": float,          # seconds
              "timestamp": float,    # midpoint, seconds
              "time_str": "mm:ss",
              "path": str,           # keyframe JPEG path
            }
        """
        try:
            from scenedetect import open_video, SceneManager  # type: ignore
            from scenedetect.detectors import ContentDetector  # type: ignore
        except ImportError as e:
            logger.error(
                "PySceneDetect chua duoc cai (%s). "
                "Chay: pip install 'scenedetect[opencv]'.", e,
            )
            return []

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            video = open_video(video_path)
            fps = float(video.frame_rate or 0.0)
            min_scene_frames = max(1, int(self.min_scene_len * fps)) if fps else 15

            sm = SceneManager()
            sm.add_detector(
                ContentDetector(
                    threshold=self.threshold,
                    min_scene_len=min_scene_frames,
                )
            )
            sm.detect_scenes(video=video, show_progress=False)
            scene_list = sm.get_scene_list()
        except Exception as e:
            logger.error("Loi khi chay PySceneDetect: %s", e)
            return []

        if not scene_list:
            logger.info(
                "Khong phat hien chuyen canh -> coi toan video la 1 scene."
            )
            try:
                duration = float(video.duration.get_seconds())  # type: ignore[attr-defined]
            except Exception:
                duration = 0.0
            scenes: List[Tuple[float, float]] = [(0.0, max(duration, 0.0))]
        else:
            scenes = [
                (start.get_seconds(), end.get_seconds())
                for start, end in scene_list
            ]

        results = self._save_keyframes(video_path, scenes, out_dir)
        logger.info("Phat hien %d scene tu %s.", len(results), video_path)
        return results

    def _save_keyframes(
        self,
        video_path: str,
        scenes: List[Tuple[float, float]],
        out_dir: Path,
    ) -> List[Dict[str, Any]]:
        """Save the midpoint frame of each scene as a JPEG via OpenCV."""
        try:
            import cv2  # type: ignore
        except ImportError:
            logger.error("OpenCV (cv2) chua co. Khong the luu keyframe.")
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Khong mo duoc video de luu keyframe: %s", video_path)
            return []

        results: List[Dict[str, Any]] = []
        try:
            for idx, (start, end) in enumerate(scenes):
                midpoint = start + max(0.0, (end - start) / 2.0)
                cap.set(cv2.CAP_PROP_POS_MSEC, midpoint * 1000.0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    logger.warning(
                        "Khong doc duoc frame cho scene %d @ %.2fs", idx, midpoint
                    )
                    continue

                fname = f"scene_{idx:04d}_{int(midpoint):06d}s.jpg"
                fpath = out_dir / fname
                if not cv2.imwrite(str(fpath), frame):
                    logger.warning("Khong ghi duoc keyframe: %s", fpath)
                    continue

                results.append(
                    {
                        "scene_index": idx,
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "timestamp": round(midpoint, 2),
                        "time_str": _format_time(midpoint),
                        "path": str(fpath),
                    }
                )
        finally:
            cap.release()

        return results
