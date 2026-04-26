"""
PaddleOCR adapter — CPU-friendly text extraction from keyframe images.

Why PaddleOCR:
  * Pure CPU, no GPU required.
  * 80+ language support including Vietnamese, English, Chinese.
  * ~0.3-1 s per typical slide on a modern laptop.
  * Mature, production-ready (Baidu).

This module is intentionally fail-soft. If `paddleocr` is not installed or
the OCR engine raises, we log a warning and return an empty string so the
orchestrator can continue without OCR (or fall through to the VLM stage).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class PaddleOCRService:
    """Lazy-init wrapper around PaddleOCR with CPU defaults."""

    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        use_gpu: bool = False,
    ):
        # PaddleOCR's `lang` parameter accepts: en, vi, ch, japan, korean, fr,
        # de, etc. Use "vi" for Vietnamese-heavy slides; "en" works reasonably
        # for code/mathy content too.
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._ocr = None

    # ------------------------------------------------------------------ #
    # Lazy initialization                                                 #
    # ------------------------------------------------------------------ #
    def _load(self) -> Optional[object]:
        if self._ocr is not None:
            return self._ocr
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError:
            logger.warning(
                "PaddleOCR chua duoc cai. Bo qua OCR. "
                "Cai bang: pip install paddleocr paddlepaddle"
            )
            return None
        try:
            self._ocr = PaddleOCR(
                use_angle_cls=self.use_angle_cls,
                lang=self.lang,
                use_gpu=self.use_gpu,
                show_log=False,
            )
            logger.info(
                "PaddleOCR san sang (lang=%s, gpu=%s).", self.lang, self.use_gpu
            )
        except Exception as e:
            logger.error("Khong khoi tao duoc PaddleOCR: %s", e)
            self._ocr = None
        return self._ocr

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #
    def extract(self, image_path: str) -> str:
        """
        OCR a single image and return concatenated text (line-separated).

        Returns "" on any failure so the caller can decide whether to fall
        through to a VLM step.
        """
        if not os.path.exists(image_path):
            logger.warning("OCR: anh khong ton tai: %s", image_path)
            return ""

        ocr = self._load()
        if ocr is None:
            return ""

        try:
            # PaddleOCR.ocr returns: List[List[ [box, (text, conf)] ]] (per page)
            result = ocr.ocr(image_path, cls=self.use_angle_cls)
        except Exception as e:
            logger.warning("PaddleOCR loi tren %s: %s", image_path, e)
            return ""

        if not result or not result[0]:
            return ""

        lines = []
        for line in result[0]:
            try:
                _box, (text, _conf) = line
            except (ValueError, TypeError):
                continue
            text = (text or "").strip()
            if text:
                lines.append(text)
        return "\n".join(lines)
