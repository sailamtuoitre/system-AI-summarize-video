"""
Per-stage checkpoint / resume helper.

Goal: never redo expensive work (Whisper transcription, scene detection,
keyframe OCR/VLM) when the developer flips a config flag (e.g.
`OCR_ENABLED`) and re-runs the pipeline on the same job, OR when a crash
forces a retry.

Storage layout (per job):

    data/jobs/{job_id}/
    ├─ video.mp4
    ├─ audio.wav            (output of MediaDemuxer)
    ├─ keyframes/           (output of SceneDetector)
    ├─ index/               (output of RAGService)
    └─ checkpoints/
       ├─ demux.json        { "audio_path": ..., "duration": ..., ... }
       ├─ scenes.json       [ keyframe_dict, keyframe_dict, ... ]
       ├─ segments.json     [ whisper_segment, ... ]
       └─ keyframes_phase4.json   (post Phase 4: with ocr_text + caption)

All artefacts are JSON for human-debuggability. Heavy binary outputs
(audio.wav, keyframe JPEGs, FAISS index) live next to them on disk and
the JSON files reference them by path.

Public API is intentionally tiny:

    cp = Checkpoint(job_dir)
    if (data := cp.load("scenes")) is None:
        data = run_expensive_stage()
        cp.save("scenes", data)

Disable globally via `CHECKPOINT_ENABLED=false` (default `true`).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.getenv("CHECKPOINT_ENABLED", "true").lower() in (
        "1", "true", "yes", "on",
    )


class Checkpoint:
    """JSON-backed per-stage cache for a single job directory."""

    def __init__(self, job_dir: str):
        self.job_dir = Path(job_dir)
        self.cp_dir = self.job_dir / "checkpoints"

    # ------------------------------------------------------------------ #
    def _path(self, name: str) -> Path:
        return self.cp_dir / f"{name}.json"

    # ------------------------------------------------------------------ #
    def load(self, name: str) -> Optional[Any]:
        """Return the cached payload for `name`, or None if absent/invalid."""
        if not _enabled():
            return None
        p = self._path(name)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Checkpoint HIT: %s (%s)", name, p)
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "Checkpoint corrupt %s -> bo qua: %s", p, e,
            )
            return None

    # ------------------------------------------------------------------ #
    def save(self, name: str, data: Any) -> None:
        """Write the payload to disk. Best-effort; never raises to caller."""
        if not _enabled():
            return
        try:
            self.cp_dir.mkdir(parents=True, exist_ok=True)
            tmp = self._path(name).with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, self._path(name))
            logger.info("Checkpoint saved: %s", name)
        except (OSError, TypeError) as e:
            logger.warning("Khong save duoc checkpoint %s: %s", name, e)

    # ------------------------------------------------------------------ #
    def has_index(self) -> bool:
        """Special-case: FAISS index lives outside the JSON checkpoint dir."""
        idx = self.job_dir / "index"
        # `default__vector_store.json` is one of the canonical files
        # llama-index writes when persisting a VectorStoreIndex.
        return idx.is_dir() and any(idx.iterdir())
