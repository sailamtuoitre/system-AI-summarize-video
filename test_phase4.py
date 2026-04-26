"""
Phase 4 smoke test — exercise the OCR + VLM cascade on a single image
without spinning up the FastAPI server or running a full video pipeline.

Usage (PowerShell):
    # Test PaddleOCR only (no API call):
    python test_phase4.py path\to\slide.jpg --no-vlm

    # Test full cascade (PaddleOCR -> Qwen-VL fallback if OCR is thin):
    python test_phase4.py path\to\slide.jpg

    # Force the VLM branch (skip OCR) to verify 9router multimodal works:
    python test_phase4.py path\to\slide.jpg --vlm-only

    # Pick a Vietnamese-friendly OCR language:
    python test_phase4.py path\to\slide.jpg --lang vi

What this does NOT do:
  - Run ffmpeg, Whisper, FAISS, or anything else from the main pipeline.
  - Mutate any state on disk besides reading the input image.

Exit codes:
  0  pipeline reached the end (even if OCR returned empty)
  2  bad arguments / image not found
  3  PaddleOCR isn't installed (run: pip install paddleocr paddlepaddle)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv

# Project imports — same modules wired into the FastAPI app
from processing.ocr_paddle import PaddleOCRService
from processing.vlm_qwen import QwenVLService
from processing.keyframe_analyzer import KeyframeAnalyzer

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("phase4_test")


def _truncate(text: str, n: int = 400) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n] + "..."


def main() -> int:
    load_dotenv()

    p = argparse.ArgumentParser(description="Phase 4 cascade smoke test")
    p.add_argument("image", help="Path to a JPEG/PNG keyframe to analyse")
    p.add_argument("--lang", default=os.getenv("OCR_LANG", "en"),
                   help="PaddleOCR language code (en/vi/ch/japan/...)")
    p.add_argument("--no-vlm", action="store_true",
                   help="Disable VLM fallback (test OCR only)")
    p.add_argument("--vlm-only", action="store_true",
                   help="Force VLM by setting OCR_MIN_TEXT_LEN very high")
    p.add_argument("--vlm-model",
                   default=os.getenv("VLM_MODEL_NAME", "qw/qwen-vl-plus"))
    args = p.parse_args()

    if not os.path.exists(args.image):
        log.error("Khong tim thay anh: %s", args.image)
        return 2

    # ------------------------------------------------------------------ OCR
    log.info("=" * 60)
    log.info("Stage 1/2: PaddleOCR (lang=%s, cpu)", args.lang)
    log.info("=" * 60)
    ocr = PaddleOCRService(lang=args.lang, use_gpu=False)
    t0 = time.time()
    ocr_text = ocr.extract(args.image)
    ocr_dt = time.time() - t0

    if ocr._ocr is None:  # noqa: SLF001 — explicit smoke-test inspection
        log.error(
            "PaddleOCR khong san sang. Cai bang: "
            "pip install paddleocr paddlepaddle"
        )
        return 3

    log.info("OCR took %.2fs, returned %d char(s).", ocr_dt, len(ocr_text))
    if ocr_text:
        log.info("---- OCR text ----\n%s\n------------------", _truncate(ocr_text))
    else:
        log.info("(OCR returned empty)")

    # ------------------------------------------------------------------ VLM
    vlm: Optional[QwenVLService] = None
    if not args.no_vlm:
        api_key = os.getenv("NINE_ROUTER_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            log.warning(
                "Khong co NINE_ROUTER_API_KEY/DASHSCOPE_API_KEY -> bo qua VLM."
            )
        else:
            vlm = QwenVLService(
                api_key=api_key,
                model_name=args.vlm_model,
                base_url=os.getenv("NINE_ROUTER_URL"),
            )

    # ---------------------------------------------------------------- Cascade
    log.info("=" * 60)
    log.info("Stage 2/2: KeyframeAnalyzer cascade")
    log.info("=" * 60)

    # If --vlm-only, set the threshold absurdly high so OCR is always "thin"
    min_len = 10**9 if args.vlm_only else int(os.getenv("OCR_MIN_TEXT_LEN", "50"))
    analyzer = KeyframeAnalyzer(ocr=ocr, vlm=vlm, ocr_min_text_len=min_len, concurrency=1)

    fake_keyframe = {
        "scene_index": 0,
        "start": 0.0,
        "end": 1.0,
        "timestamp": 0.0,
        "time_str": "00:00",
        "path": args.image,
    }

    t0 = time.time()
    [enriched] = analyzer.analyze([fake_keyframe])
    cascade_dt = time.time() - t0

    log.info("Cascade took %.2fs.", cascade_dt)
    log.info("ocr_text len=%d | caption len=%d | used_vlm=%s",
             len(enriched.get("ocr_text", "")),
             len(enriched.get("caption", "")),
             enriched.get("analysis_used_vlm"))
    if enriched.get("caption"):
        log.info("---- VLM caption ----\n%s\n---------------------",
                 _truncate(enriched["caption"]))

    log.info("=" * 60)
    log.info("Phase 4 smoke OK. ocr=%.2fs cascade=%.2fs total=%.2fs",
             ocr_dt, cascade_dt, ocr_dt + cascade_dt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
