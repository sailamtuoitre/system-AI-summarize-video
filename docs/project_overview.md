# Tổng quan Dự án: MVP AI Video Assistant (v0.5)

## Cập nhật v0.5 (Phase 2)
- Scene detection ∥ Whisper transcription (ThreadPoolExecutor 2 worker).
- Map phase trong Generation chạy song song theo `MAP_PHASE_CONCURRENCY` (mặc định 4).
- Hardened JSON parsing: skip flashcard/quiz thiếu trường thay vì crash cả chunk.

## Cập nhật v0.4 (Phase 0 + Phase 1)
- Sửa toàn bộ lỗi P0 (pydantic v2, python-multipart, llama-index-llms-openai, embed model global, init flashcards/quiz, UUID validation, file size cap, streamed upload).
- Loại bỏ moviepy khỏi hot path; thay bằng một lệnh `ffmpeg` (`MediaDemuxer`).
- Thay vòng pixel-diff bằng PySceneDetect (`SceneDetector`).
- Whisper chạy trên toàn bộ audio.wav một lần (không còn cộng offset chunk).
- Thêm biến môi trường để tinh chỉnh: `FRAME_SAMPLE_FPS`, `SCENE_THRESHOLD`, `MIN_SCENE_LEN_SEC`, `WHISPER_MODEL_SIZE`, `MAX_UPLOAD_BYTES`, `LOG_LEVEL`.

## 1. Giới thiệu
Công cụ hỗ trợ học tập thông minh dựa trên video bài giảng. Hệ thống dùng AI đa phương thức để "nghe" (Whisper) và "xem" (PySceneDetect + keyframes) nội dung video, phục vụ tóm tắt, hỏi đáp, flashcards và quiz.

## 2. Mục tiêu
- Xử lý ổn định video bài giảng dài (>60 phút).
- Kết hợp lời giảng và slide (qua keyframe) để tạo bằng chứng trực quan.
- Cung cấp chatbot Q&A có trích dẫn timestamp.

## 3. Phạm vi MVP
- **Input:** Video MP4 (giới hạn `MAX_UPLOAD_BYTES`, mặc định 500 MB).
- **Tính năng tự động:**
  - Multi-modal Summary (Map-Reduce).
  - Visual Evidence (keyframe per scene).
  - Auto Flashcards và Auto Mini-test.
- **Tính năng tương tác:**
  - Chat Q&A (POST `/job/{id}/chat`).
  - Studio Panel.

## 4. Công nghệ AI

| Thành phần | Provider | Vai trò |
|-----------|----------|---------|
| **ffmpeg / ffprobe** | Local binary | Demux audio + sample frame một lượt |
| **PySceneDetect** | `scenedetect[opencv]` | Phát hiện chuyển scene |
| **faster-whisper** | Local | Speech-to-text |
| **HuggingFace MiniLM** | `sentence-transformers/all-MiniLM-L6-v2` | Embedding |
| **FAISS** | `faiss-cpu` qua LlamaIndex | Vector store |
| **Qwen (qua 9router)** | Alibaba / 9router | LLM tóm tắt, Q&A, flashcards, quiz |

## 5. Kỹ thuật xử lý video dài
1. **Demux một lượt** — không tốn nhiều lần decode.
2. **Whisper full-audio** — không có ranh giới chunk gây mất ngữ cảnh.
3. **Map-Reduce summary** — Map theo cụm 15 node, Reduce tổng hợp.

## 6. Giao diện
React Web App (`apps/web-ui`), Vite dev server tại `:5173`. Layout 3 panel.

## 7. Yêu cầu cài đặt
- Python 3.9+
- Node.js 16+
- **ffmpeg + ffprobe** trong PATH (Phase 1)
- 9router cài đặt và chạy tại `NINE_ROUTER_URL`

## 8. Lộ trình
- ✅ **Phase 3 (v0.6):** Whisper tuning — beam_size=1, VAD chặt hơn, cpu_threads, num_workers, language pin, confidence filter.
- **Stage T (transcript-driven gating):** phân loại video bằng từ vựng deixis (`slide`, `như các bạn thấy`, ...).
- **Stage C:** phash dedup + brightness gate cho keyframe.
- **OCR + VLM cascade:** PaddleOCR mặc định, Qwen-VL chỉ khi OCR quá ít chữ.
- **Per-stage checkpoint:** resume sau crash.
- **Cluster-based summary + structured JSON output.**
