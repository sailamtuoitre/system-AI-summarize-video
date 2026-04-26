"""
Qwen-VL via 9router — vision-language captioning for keyframes that lack
extractable text (charts, diagrams, photos, handwriting).

Reuses the existing 9router OpenAI-compatible endpoint that the project
already points its text LLM at, so no new infrastructure is needed.

Default model: `qw/qwen-vl-plus` (override via VLM_MODEL_NAME env). The
model name should be whatever your 9router instance exposes for the
multimodal Qwen variant.

Fail-soft: any HTTP / parsing error returns an empty string so the
orchestrator can fall back to OCR-only or skip the keyframe entirely.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


_DEFAULT_PROMPT = (
    "You are analyzing a frame from an educational video (lecture slide, "
    "code editor, diagram, or whiteboard). In 1-3 short sentences, describe "
    "the visible content in the same language as the text on the image "
    "(Vietnamese if Vietnamese, English if English). Include any numbers, "
    "labels, axis names, or formulae you can read. Be concise; no preamble."
)


class QwenVLService:
    """Caption an image via a multimodal Qwen model on a 9router endpoint."""

    def __init__(
        self,
        api_key: Optional[str],
        model_name: str = "qw/qwen-vl-plus",
        base_url: Optional[str] = None,
        prompt: Optional[str] = None,
        timeout: float = 30.0,
        max_tokens: int = 256,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.prompt = prompt or _DEFAULT_PROMPT
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._client = None

    # ------------------------------------------------------------------ #
    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            logger.error(
                "Goi VLM can openai SDK (`pip install openai`). Bo qua."
            )
            return None
        if not self.api_key:
            logger.warning(
                "VLM khong co API key (NINE_ROUTER_API_KEY/DASHSCOPE_API_KEY). "
                "Tat caption."
            )
            return None
        try:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        except Exception as e:
            logger.error("Khong khoi tao duoc OpenAI client cho VLM: %s", e)
            self._client = None
        return self._client

    # ------------------------------------------------------------------ #
    @staticmethod
    def _encode_image(image_path: str) -> Optional[str]:
        """Return a `data:image/jpeg;base64,...` URL or None on failure."""
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError as e:
            logger.warning("VLM: khong doc duoc anh %s: %s", image_path, e)
            return None
        ext = os.path.splitext(image_path)[1].lower().lstrip(".") or "jpeg"
        if ext == "jpg":
            ext = "jpeg"
        return f"data:image/{ext};base64,{b64}"

    # ------------------------------------------------------------------ #
    def describe(self, image_path: str) -> str:
        """
        Send the image to the multimodal LLM and return a short caption.

        Returns "" on any failure so the cascade can degrade gracefully.
        """
        if not os.path.exists(image_path):
            logger.warning("VLM: anh khong ton tai: %s", image_path)
            return ""

        client = self._get_client()
        if client is None:
            return ""

        data_url = self._encode_image(image_path)
        if data_url is None:
            return ""

        try:
            resp = client.chat.completions.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=0.2,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    }
                ],
            )
        except Exception as e:
            logger.warning(
                "VLM goi that bai cho %s: %s", os.path.basename(image_path), e
            )
            return ""

        try:
            text = (resp.choices[0].message.content or "").strip()
        except (AttributeError, IndexError, TypeError):
            return ""
        return text
