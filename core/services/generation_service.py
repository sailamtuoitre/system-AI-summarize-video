import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from llama_index.llms.openai import OpenAI
from core.domain.models import SummaryOutput, Flashcard, QuizQuestion, Evidence
import json

# Maximum number of concurrent LLM calls during the Map phase. Tune via env
# to respect 9router rate limits. 4-6 is a good default for most Qwen plans.
MAP_PHASE_CONCURRENCY = int(os.getenv("MAP_PHASE_CONCURRENCY", "4"))

logger = logging.getLogger(__name__)

class GenerationService:
    """
    Dịch vụ sinh nội dung sử dụng LLM (Alibaba Qwen) thông qua DashScope.
    """

    def __init__(self, api_key: str, model_name: str = "qwen-3.6-plus", base_url: Optional[str] = None):
        """
        Khởi tạo GenerationService.

        Args:
            api_key (str): API Key (từ 9router hoặc trực tiếp).
            model_name (str): Tên mô hình sử dụng.
            base_url (str, optional): Base URL cho API (dùng cho 9router).
        """
        self.llm = OpenAI(model=model_name, api_key=api_key, api_base=base_url)
        self.model_name = model_name
        # Initialize extracted materials so get_extracted_materials() never raises
        # AttributeError if called before generate_summary().
        self.extracted_flashcards: List[Flashcard] = []
        self.extracted_quiz: List[QuizQuestion] = []
        logger.info(f"Đã khởi tạo GenerationService với mô hình: {model_name} qua {base_url or 'Direct API'}")

    def generate_summary(self, context_nodes: List[Dict[str, Any]]) -> SummaryOutput:
        """
        Sinh tóm tắt và đồng thời trích xuất Flashcards/Quiz (Concurrent Extraction).
        Sử dụng Map-Reduce tối ưu cho video dài với Qwen 3.6 Plus.
        """
        if not context_nodes:
            return SummaryOutput(initial_summary="Không có nội dung để tóm tắt.")

        # Ngưỡng chia chunk: 15 nodes (~7 phút nội dung)
        CHUNK_SIZE = 15
        node_chunks = [context_nodes[i:i + CHUNK_SIZE] for i in range(0, len(context_nodes), CHUNK_SIZE)]
        
        all_partials: List[str] = [""] * len(node_chunks)  # preserve chunk order
        self.extracted_flashcards = []
        self.extracted_quiz = []

        def _build_map_prompt(idx: int, chunk: List[Dict[str, Any]]) -> str:
            chunk_text = "\n".join(
                f"[{n['metadata']['timestamp_mmss']}] {n['text']}" for n in chunk
            )
            return (
                f"Đây là phần {idx+1}/{len(node_chunks)} của một video bài giảng:\n\n{chunk_text}\n\n"
                "Nhiệm vụ của bạn:\n"
                "1. Tóm tắt 3-5 ý chính của đoạn này.\n"
                "2. Tạo 2 Flashcards quan trọng (Front/Back/Evidence/Timestamp).\n"
                "3. Tạo 2 câu hỏi trắc nghiệm (Question/Options/Answer/Explanation/Timestamp).\n\n"
                "Yêu cầu trả về định dạng JSON duy nhất:\n"
                "{\n"
                "  \"summary\": \"Các ý chính...\",\n"
                "  \"flashcards\": [{\"front\": \"...\", \"back\": \"...\", \"quote\": \"...\", \"timestamp\": \"mm:ss\"}],\n"
                "  \"quiz\": [{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": \"...\", \"explanation\": \"...\", \"timestamp\": \"mm:ss\"}]\n"
                "}"
            )

        def _run_one(idx: int, chunk: List[Dict[str, Any]]) -> tuple[int, Optional[Dict[str, Any]]]:
            """Run a single Map prompt; returns (chunk_index, parsed_data_or_None)."""
            try:
                response = self.llm.complete(_build_map_prompt(idx, chunk))
                text = response.text
                start = text.find("{")
                end = text.rfind("}") + 1
                if start == -1 or end <= start:
                    raise ValueError("Khong tim thay JSON trong phan hoi LLM")
                return idx, json.loads(text[start:end])
            except Exception as e:
                logger.error("Loi Map phase tai chunk %d: %s", idx + 1, e)
                return idx, None

        # Giai đoạn 1: Map (chạy song song để giảm latency tổng).
        max_workers = max(1, min(MAP_PHASE_CONCURRENCY, len(node_chunks)))
        logger.info(
            "Map phase: %d chunk, concurrency=%d", len(node_chunks), max_workers
        )
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="map"
        ) as pool:
            futures = [
                pool.submit(_run_one, i, chunk)
                for i, chunk in enumerate(node_chunks)
            ]
            for fut in as_completed(futures):
                idx, data = fut.result()
                if data is None:
                    continue
                chunk = node_chunks[idx]
                source_node = chunk[0] if chunk else None
                source_id = source_node["node_id"] if source_node else "unknown"

                all_partials[idx] = data.get("summary", "")

                for card in data.get("flashcards", []) or []:
                    try:
                        self.extracted_flashcards.append(
                            Flashcard(
                                front=card["front"],
                                back=card["back"],
                                evidence=Evidence(
                                    timestamp=card.get("timestamp", "00:00"),
                                    quote=card.get("quote", ""),
                                    source_node_id=source_id,
                                ),
                            )
                        )
                    except (KeyError, TypeError) as e:
                        logger.warning(
                            "Bo qua flashcard malformed o chunk %d: %s", idx + 1, e
                        )

                for q in data.get("quiz", []) or []:
                    try:
                        self.extracted_quiz.append(
                            QuizQuestion(
                                question=q["question"],
                                options=q["options"],
                                answer=q["answer"],
                                explanation=q.get("explanation", ""),
                                evidence=Evidence(
                                    timestamp=q.get("timestamp", "00:00"),
                                    quote="",
                                    source_node_id=source_id,
                                ),
                            )
                        )
                    except (KeyError, TypeError) as e:
                        logger.warning(
                            "Bo qua quiz malformed o chunk %d: %s", idx + 1, e
                        )

                logger.info(
                    "Da trich xuat xong kien thuc cho chunk %d/%d",
                    idx + 1,
                    len(node_chunks),
                )

        # Giai đoạn 2: Reduce (Tổng hợp bản tóm tắt cuối cùng)
        full_context = "\n\n".join(all_partials)
        reduce_prompt = (
            "Dựa trên các ý chính sau từ một video bài giảng:\n\n"
            f"{full_context}\n\n"
            "Hãy viết một bản tóm tắt hoàn chỉnh, chuyên nghiệp (200-300 từ) bằng tiếng Việt."
        )
        
        final_summary = self.llm.complete(reduce_prompt).text.strip()
        logger.info("Đã hoàn tất Reduce phase. Toàn bộ kiến thức đã được sẵn sàng.")
        
        return SummaryOutput(initial_summary=final_summary)

    def get_extracted_materials(self) -> Dict[str, List[Any]]:
        """Trả về danh sách flashcards và quiz đã trích xuất được."""
        return {
            "flashcards": self.extracted_flashcards,
            "quiz": self.extracted_quiz
        }

    def answer_question(self, question: str, context_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Trả lời câu hỏi người dùng dựa trên dữ liệu video.
        
        Args:
            question (str): Câu hỏi của người dùng.
            context_nodes (List[Dict[str, Any]]): Các đoạn transcript liên quan.
            
        Returns:
            Dict[str, Any]: Câu trả lời kèm bằng chứng.
        """
        context_parts = []
        for i, n in enumerate(context_nodes):
            meta = n["metadata"]
            context_parts.append(f"[{i}] (Thời gian: {meta['timestamp_mmss']}): {n['text']}")
        
        context_text = "\n".join(context_parts)
        
        prompt = (
            f"Bạn là một trợ lý học tập AI. Hãy trả lời câu hỏi sau dựa trên thông tin từ bài giảng:\n"
            f"Câu hỏi: {question}\n\n"
            f"Thông tin trích dẫn:\n{context_text}\n\n"
            "Yêu cầu trả lời:\n"
            "1. Chỉ sử dụng thông tin được cung cấp.\n"
            "2. Ghi chú rõ thời gian (mm:ss) của bằng chứng trong câu trả lời.\n"
            "3. Nếu không có thông tin, hãy nói bạn không biết, đừng bịa ra."
        )
        
        response = self.llm.complete(prompt)

        # Build rich citation objects so the UI can show badges for slide
        # text (OCR) vs AI caption (VLM) per source.
        sources_rich: List[Dict[str, Any]] = []
        for n in context_nodes:
            meta = n.get("metadata", {}) or {}
            sources_rich.append({
                "timestamp": meta.get("timestamp_mmss", "00:00"),
                "has_ocr": bool(meta.get("has_ocr")),
                "has_caption": bool(meta.get("has_caption")),
                "has_visual_evidence": bool(meta.get("has_visual_evidence")),
            })
        return {
            "answer": response.text.strip(),
            # Backwards-compat: keep `sources` as a list of timestamps strings
            # so existing clients keep working. New clients should prefer
            # `source_details`.
            "sources": [s["timestamp"] for s in sources_rich],
            "source_details": sources_rich,
        }

    def generate_flashcards(self, context_nodes: List[Dict[str, Any]]) -> List[Flashcard]:
        """
        Sinh danh sách các thẻ ghi nhớ.
        """
        # (Chi tiết implementation sẽ được tối ưu với JSON output của Gemini)
        # Để đơn giản hóa cho MVP v0.1, chúng ta sinh 3-5 cards từ context
        context_text = "\n".join([f"Time: {n['metadata']['timestamp_mmss']} | Content: {n['text']}" for n in context_nodes])
        
        prompt = (
            f"Dựa trên nội dung bài giảng:\n{context_text}\n\n"
            "Hãy tạo 5 thẻ ghi nhớ (Flashcards). Mỗi thẻ gồm:\n"
            "- Front: Khái niệm hoặc câu hỏi ngắn.\n"
            "- Back: Giải thích chi tiết.\n"
            "- Latex: Công thức toán học nếu có (để trong dấu $$...$$).\n"
            "- Evidence Quote: Câu trích dẫn nguyên văn ngắn gọn.\n"
            "- Timestamp: Mốc mm:ss của trích dẫn đó.\n\n"
            "Trả về định dạng JSON list các object: "
            "[{\"front\": \"...\", \"back\": \"...\", \"latex\": \"...\", \"quote\": \"...\", \"timestamp\": \"...\", \"node_id\": \"...\"}]"
        )
        
        response = self.llm.complete(prompt)
        # Giả lập việc parse JSON (trong thực tế sẽ dùng JsonOutputParser của LangChain/LlamaIndex)
        try:
            # Tìm đoạn JSON trong response
            text = response.text
            start = text.find('[')
            end = text.rfind(']') + 1
            cards_data = json.loads(text[start:end])
            
            flashcards = []
            for item in cards_data:
                flashcards.append(Flashcard(
                    front=item["front"],
                    back=item["back"],
                    latex=item.get("latex"),
                    evidence=Evidence(
                        timestamp=item["timestamp"],
                        quote=item["quote"],
                        source_node_id=item.get("node_id", "unknown")
                    )
                ))
            return flashcards
        except:
            logger.error("Lỗi parse JSON flashcards từ LLM.")
            return []

    def generate_quiz(self, context_nodes: List[Dict[str, Any]]) -> List[QuizQuestion]:
        """
        Sinh danh sách 10 câu hỏi trắc nghiệm dựa trên nội dung bài giảng.
        """
        context_text = "\n".join([f"Content: {n['text']}" for n in context_nodes])
        
        prompt = (
            f"Dựa trên nội dung bài giảng:\n{context_text}\n\n"
            "Hãy tạo 5 câu hỏi trắc nghiệm (Mini-test). Mỗi câu gồm:\n"
            "- Question: Câu hỏi rõ ràng.\n"
            "- Options: List 4 phương án trả lời.\n"
            "- Answer: Đáp án đúng duy nhất.\n"
            "- Explanation: Giải thích ngắn gọn.\n"
            "- Quote: Trích dẫn chứng minh.\n"
            "- Timestamp: Mốc mm:ss của trích dẫn.\n\n"
            "Trả về định dạng JSON list các object: "
            "[{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": \"...\", \"explanation\": \"...\", \"quote\": \"...\", \"timestamp\": \"...\"}]"
        )
        
        response = self.llm.complete(prompt)
        try:
            text = response.text
            start = text.find('[')
            end = text.rfind(']') + 1
            quiz_data = json.loads(text[start:end])
            
            questions = []
            for item in quiz_data:
                questions.append(QuizQuestion(
                    question=item["question"],
                    options=item["options"],
                    answer=item["answer"],
                    explanation=item["explanation"],
                    evidence=Evidence(
                        timestamp=item["timestamp"],
                        quote=item["quote"],
                        source_node_id="unknown"
                    )
                ))
            return questions
        except:
            logger.error("Lỗi parse JSON quiz từ LLM.")
            return []
