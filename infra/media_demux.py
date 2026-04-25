"""
Single-pass media demuxer.

Replaces moviepy-based VideoChunker + AudioExtractor with one ffmpeg
invocation per artifact. Produces:
  - audio.wav  (16 kHz, mono, PCM s16le -- ready for faster-whisper)
  - frames/    (1 fps JPEG samples for visual analysis)
  - MediaInfo  (duration, fps, resolution, codecs, has_audio)

Why: removes 2-3 redundant decode passes done by moviepy and avoids the
moviepy 2.x removal of `moviepy.editor`.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MediaInfo:
    """Lightweight metadata extracted via ffprobe."""

    duration: float          # seconds
    fps: float               # frames per second of the primary video stream
    width: int
    height: int
    has_audio: bool
    video_codec: Optional[str]
    audio_codec: Optional[str]


class MediaDemuxError(RuntimeError):
    """Raised when ffmpeg/ffprobe fail or are unavailable."""


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise MediaDemuxError(
            f"'{name}' khong co trong PATH. Hay cai ffmpeg "
            "(https://ffmpeg.org) va dam bao 'ffmpeg' va 'ffprobe' chay duoc."
        )
    return path


def probe(video_path: str) -> MediaInfo:
    """Run ffprobe and return parsed media info."""
    ffprobe = _require_binary("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaDemuxError(f"ffprobe that bai: {result.stderr.strip()}")

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video_stream is None:
        raise MediaDemuxError("Khong tim thay luong video trong file.")

    # Parse fps from "30000/1001" form.
    fps_raw = (
        video_stream.get("avg_frame_rate")
        or video_stream.get("r_frame_rate")
        or "0/1"
    )
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)

    return MediaInfo(
        duration=duration,
        fps=fps,
        width=int(video_stream.get("width") or 0),
        height=int(video_stream.get("height") or 0),
        has_audio=audio_stream is not None,
        video_codec=video_stream.get("codec_name"),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
    )


def extract_audio(
    video_path: str,
    audio_output_path: str,
    sample_rate: int = 16000,
) -> bool:
    """
    Extract a 16 kHz mono WAV from the input video in a single ffmpeg pass.

    Returns False if the video has no audio stream or ffmpeg fails.
    """
    ffmpeg = _require_binary("ffmpeg")
    out = Path(audio_output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-loglevel", "error",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(out),
    ]
    logger.info("Tach audio bang ffmpeg -> %s", out)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.error("ffmpeg audio extract that bai: %s", stderr)
        return False
    return out.exists() and out.stat().st_size > 0


def extract_frames(
    video_path: str,
    frames_output_dir: str,
    fps: float = 1.0,
    max_width: int = 640,
    quality: int = 3,
) -> List[str]:
    """
    Sample frames at `fps` per second (default 1) and save as JPEG.

    Returns list of generated frame paths sorted by index.
    """
    ffmpeg = _require_binary("ffmpeg")
    out_dir = Path(frames_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = str(out_dir / "frame_%06d.jpg")
    # Downscale only if the source is wider than max_width; preserve aspect ratio.
    vf = f"fps={fps},scale='min({max_width},iw)':-1"

    cmd = [
        ffmpeg,
        "-y",
        "-loglevel", "error",
        "-i", video_path,
        "-vf", vf,
        "-q:v", str(quality),
        pattern,
    ]
    logger.info("Lay frame bang ffmpeg -> %s", out_dir)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg frame extract that bai: %s", (result.stderr or "").strip())
        return []

    return sorted(str(p) for p in out_dir.glob("frame_*.jpg"))


@dataclass
class DemuxResult:
    audio_path: Optional[str]
    frames_dir: str
    frame_paths: List[str]
    media_info: MediaInfo


class MediaDemuxer:
    """
    High-level facade used by the orchestrator.

    Usage:
        demuxer = MediaDemuxer()
        result = demuxer.run(video_path, job_dir)
        # result.audio_path -> path to audio.wav (or None if no audio stream)
        # result.frame_paths -> list of 1 fps frame JPEGs
        # result.media_info  -> MediaInfo dataclass
    """

    def __init__(self, audio_sample_rate: int = 16000, frame_fps: float = 1.0):
        self.audio_sample_rate = audio_sample_rate
        self.frame_fps = frame_fps

    def run(self, video_path: str, output_dir: str) -> DemuxResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        info = probe(video_path)
        logger.info(
            "Media probe: duration=%.1fs fps=%.2f res=%dx%d audio=%s",
            info.duration, info.fps, info.width, info.height, info.has_audio,
        )

        audio_path: Optional[str] = None
        if info.has_audio:
            target_audio = str(out / "audio.wav")
            if extract_audio(video_path, target_audio, self.audio_sample_rate):
                audio_path = target_audio
            else:
                logger.warning("Khong tach duoc audio mac du co stream audio.")

        frames_dir = str(out / "frames")
        frame_paths = extract_frames(video_path, frames_dir, fps=self.frame_fps)

        return DemuxResult(
            audio_path=audio_path,
            frames_dir=frames_dir,
            frame_paths=frame_paths,
            media_info=info,
        )
