"""
Stage T — transcript-driven gating for the OCR/VLM cascade.

Heuristic: if the speaker never refers to anything visual (no deixis words
like "slide", "as you can see", "this code", "this chart", "hình bên",
"như các bạn thấy", ...), then the keyframes are almost certainly just a
static talking head and Phase 4 brings little value while costing real
time/$.

This gate is intentionally conservative — it only suggests SKIP when
*none* of a generous list of visual-pointer cues appear in the transcript.
Otherwise it passes through and Phase 4 runs as normal.

Pure functions, no side effects, no external dependencies.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Iterable, List, Sequence

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Deixis vocabulary
# --------------------------------------------------------------------------- #
# Vietnamese — slide / lecture phrases.
_VI_CUES = [
    "slide",
    "trang này",
    "hình bên",
    "hình trên",
    "biểu đồ",
    "sơ đồ",
    "hình vẽ",
    "công thức",
    "bảng này",
    "đoạn code",
    "đoạn mã",
    "ví dụ này",
    "ở đây",
    "ở trên",
    "ở dưới",
    "bên trái",
    "bên phải",
    "như các bạn thấy",
    "như mọi người thấy",
    "như chúng ta thấy",
    "như các em thấy",
    "trên màn hình",
    "trên bảng",
    "ghi chú",
    "đường này",
    "phương trình",
    "đồ thị",
]

# English — same idea.
_EN_CUES = [
    "slide",
    "this code",
    "this chart",
    "this graph",
    "this diagram",
    "this figure",
    "this table",
    "this equation",
    "this formula",
    "this example",
    "as you can see",
    "as we can see",
    "look at this",
    "look here",
    "on the screen",
    "on the board",
    "on the right",
    "on the left",
    "the arrow",
    "the highlighted",
    "the box",
    "shown here",
    "shown above",
    "shown below",
    "depicted",
    "illustrated",
]

DEFAULT_CUES: List[str] = sorted(set(c.lower() for c in _VI_CUES + _EN_CUES))


# --------------------------------------------------------------------------- #
# Tunables
# --------------------------------------------------------------------------- #
# How many distinct cue *hits* are required to consider the video visual.
# 1 is permissive: even a single "slide" mention turns Phase 4 on.
DEIXIS_MIN_HITS = int(os.getenv("DEIXIS_MIN_HITS", "1"))


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def transcript_text(segments: Sequence[dict]) -> str:
    """Concatenate Whisper segments into a single lowercased string."""
    parts: List[str] = []
    for seg in segments:
        t = (seg.get("text") or "").strip()
        if t:
            parts.append(t)
    return " ".join(parts).lower()


def count_deixis_hits(text_lower: str, cues: Iterable[str] = DEFAULT_CUES) -> int:
    """
    Count distinct deixis cues that appear at least once in the text.

    We use word-boundary regexes so "slideshow" doesn't false-positive on
    "slide", but tolerate diacritics by matching against the lowercased
    transcript as-is (Whisper output keeps diacritics).
    """
    if not text_lower:
        return 0
    hits = 0
    for cue in cues:
        # Phrases with spaces use plain substring search (faster + still
        # accurate enough for multi-word cues like "as you can see").
        if " " in cue:
            if cue in text_lower:
                hits += 1
        else:
            # Word-boundary match for single tokens.
            if re.search(rf"\b{re.escape(cue)}\b", text_lower):
                hits += 1
    return hits


def should_run_visual_stage(
    segments: Sequence[dict],
    min_hits: int = DEIXIS_MIN_HITS,
) -> tuple[bool, int]:
    """
    Decide whether Phase 4 (OCR + VLM cascade) should run.

    Returns (run: bool, hits: int).

    - `run=True`  → at least `min_hits` cues found, video is visual-y.
    - `run=False` → talk-head video, skip Phase 4 to save time/$.

    Always returns True when `min_hits <= 0` (cheap escape hatch to disable
    the gate entirely without removing the call site).
    """
    if min_hits <= 0:
        return True, 0
    if not segments:
        # No transcript at all — could be a silent slide deck. Run Phase 4
        # so we still get visual content.
        return True, 0

    text = transcript_text(segments)
    hits = count_deixis_hits(text)
    decision = hits >= min_hits
    logger.info(
        "Stage T: %d deixis cue(s) found in transcript -> %s Phase 4.",
        hits, "RUN" if decision else "SKIP",
    )
    return decision, hits
