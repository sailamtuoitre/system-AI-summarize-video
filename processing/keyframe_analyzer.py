"""
Keyframe analysis cascade: PaddleOCR -> (optional) Qwen-VL caption.

Strategy (CPU-friendly, GPU-free):
  1. Run PaddleOCR on every keyframe (fast, deterministic).
  2. If extracted text length < OCR_MIN_TEXT_LEN, the slide is probably a
     chart / diagram / photo — fall through to Qwen-VL via 9router for a
     short natural-language description.
  3. Concatenate text + caption (whichever exist) into the keyframe's
     analysis dict.

Both stages are fail-soft: if a backend is missing or errors, we record
an empty string and continue. The orchestrator can choose to skip the
whole stage by setting OCR_ENABLED=false.

Concurrency:
  Keyframes are processed in parallel via ThreadPoolExecutor. PaddleOCR
  releases the GIL during inference, and Qwen-VL calls are network-bound,
  so threads overlap effectively on CPU.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from processing.ocr_paddle import PaddleOCRService
from processing.vlm_qwen import QwenVLService

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Tuning knobs (env-tunable)
# --------------------------------------------------------------------------- #
OCR_MIN_TEXT_LEN = int(os.getenv("OCR_MIN_TEXT_LEN", "50"))
KEYFRAME_CONCURRENCY = int(os.getenv("KEYFRAME_CONCURRENCY", "4"))


class KeyframeAnalyzer:
    """
    Analyse keyframes with the OCR -> VLM cascade.

    Args:
        ocr: PaddleOCRService instance (fail-soft if Paddle isn't installed).
        vlm: Optional QwenVLService; if None, only OCR runs.
        ocr_min_text_len: text length below which we treat the OCR output as
            "thin" and fall through to VLM captioning.
        concurrency: max parallel keyframes processed at once.
    """

    def __init__(
        self,
        ocr: Optional[PaddleOCRService] = None,
        vlm: Optional[QwenVLService] = None,
        ocr_min_text_len: int = OCR_MIN_TEXT_LEN,
        concurrency: int = KEYFRAME_CONCURRENCY,
    ):
        self.ocr = ocr
        self.vlm = vlm
        self.ocr_min_text_len = ocr_min_text_len
        self.concurrency = max(1, concurrency)

    # ------------------------------------------------------------------ #
    def _analyze_one(self, kf: Dict[str, Any]) -> Dict[str, Any]:
        """Cascade for a single keyframe. Returns a dict merged into the kf."""
        path = kf.get("path")
        ocr_text = ""
        caption = ""

        if self.ocr is not None and path:
            try:
                ocr_text = self.ocr.extract(path)
            except Exception as e:  # belt-and-braces; OCR layer already swallows
                logger.warning("OCR exception tren %s: %s", path, e)
                ocr_text = ""

        # Fall through to VLM if OCR is thin
        if (
            self.vlm is not None
            and path
            and len(ocr_text.strip()) < self.ocr_min_text_len
        ):
            try:
                caption = self.vlm.describe(path)
            except Exception as e:
                logger.warning("VLM exception tren %s: %s", path, e)
                caption = ""

        return {
            "ocr_text": ocr_text,
            "caption": caption,
            "analysis_used_vlm": bool(caption),
        }

    # ------------------------------------------------------------------ #
    def analyze(self, keyframes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run the cascade across all keyframes in parallel.

        Returns the input list with each item augmented by:
            - ocr_text: str
            - caption: str
            - analysis_used_vlm: bool
        Order is preserved (results are placed back at the original index).
        """
        if not keyframes:
            return []
        if self.ocr is None and self.vlm is None:
            logger.info("KeyframeAnalyzer: ca OCR lan VLM deu tat. Bo qua.")
            return keyframes

        t0 = time.time()
        results: List[Optional[Dict[str, Any]]] = [None] * len(keyframes)
        with ThreadPoolExecutor(
            max_workers=self.concurrency, thread_name_prefix="kf-analyze"
        ) as pool:
            futures = {
                pool.submit(self._analyze_one, kf): idx
                for idx, kf in enumerate(keyframes)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    extra = fut.result()
                except Exception as e:
                    logger.warning("Keyframe analyze that bai @%d: %s", idx, e)
                    extra = {"ocr_text": "", "caption": "", "analysis_used_vlm": False}
                merged = dict(keyframes[idx])
                merged.update(extra)
                results[idx] = merged

        # Replace any leftover Nones (shouldn't happen) with originals
        out = [
            r if r is not None else dict(keyframes[i])
            for i, r in enumerate(results)
        ]
        n_ocr = sum(1 for r in out if r.get("ocr_text"))
        n_vlm = sum(1 for r in out if r.get("analysis_used_vlm"))
        logger.info(
            "KeyframeAnalyzer: %d frame trong %.2fs (ocr=%d, vlm=%d).",
            len(out), time.time() - t0, n_ocr, n_vlm,
        )
        return out
