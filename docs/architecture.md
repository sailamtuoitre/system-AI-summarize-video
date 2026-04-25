# Kiến trúc Hệ thống: Multi-modal RAG Pipeline (v0.6)

## Cập nhật v0.6 (Phase 3 — Whisper tuning)
- `TranscriptionService` được tinh chỉnh nhiều tham số có thể đổi qua env:
  - `WHISPER_BEAM_SIZE=1` (mặc định mới): nhanh ~2× so với beam=5, mất ~1% WER.
  - `WHISPER_VAD_MIN_SILENCE_MS=300` + `WHISPER_VAD_THRESHOLD=0.45`: VAD chặt hơn → loại bỏ thêm im lặng → bớt audio Whisper phải xử lý.
  - `WHISPER_CPU_THREADS=0` (auto = `os.cpu_count()`) + `WHISPER_NUM_WORKERS=2`: bật pipeline parallelism nội bộ của ctranslate2.
  - `WHISPER_LANGUAGE`: pin ngôn ngữ (vd. `vi`, `en`) để bỏ bước auto-detect (tiết kiệm 1-3s).
  - `WHISPER_MIN_CONFIDENCE`: lọc segment có `avg_logprob` thấp (thường là hallucination trên im lặng/nhạc nền).
- `condition_on_previous_text=False` để giảm hiện tượng lặp/hallucination loop trên video dài.
- Log transcription giờ in `language`, `language_probability`, số segment bị drop do confidence thấp.
- Kỳ vọng: cắt thêm ~30-40% thời gian Whisper trên audio dài (8 min → 5-6 min cho 1h video).

## Cập nhật v0.5 (Phase 2 — Parallelism)
- **Scene detection chạy song song với Whisper transcription** trong `VideoOrchestrator` qua `ThreadPoolExecutor` (cả hai đều giải phóng GIL: ctranslate2 cho faster-whisper, OpenCV/numpy cho PySceneDetect).
- **Map phase trong `GenerationService.generate_summary` chạy song song** N tác vụ LLM (mặc định `MAP_PHASE_CONCURRENCY=4`). Reduce vẫn tuần tự sau khi tất cả Map hoàn tất. Tóm tắt từng đoạn được gom theo đúng thứ tự gốc bất kể thứ tự hoàn tất.
- Hardened JSON parsing trong Map: bỏ qua flashcard/quiz thiếu trường thay vì crash cả chunk.
- Biến môi trường mới: `MAP_PHASE_CONCURRENCY`.

## Cập nhật v0.4 (Phase 0 + Phase 1)
- **Phase 0 — sửa lỗi và bảo mật:**
  - Streamed upload + giới hạn dung lượng (`MAX_UPLOAD_BYTES`, mặc định 500 MB).
  - `job_id` được validate là UUID trên mọi endpoint per-job (chống path traversal).
  - `file.filename` được kiểm tra null + so sánh đuôi `.mp4` không phân biệt hoa thường.
  - Pydantic v2: `min_items` / `max_items` → `min_length` / `max_length`.
  - `Settings.embed_model` được đăng ký global trong LlamaIndex để query embedding dùng HuggingFace thay vì OpenAI mặc định.
  - `extracted_flashcards` / `extracted_quiz` được khởi tạo trong `__init__` của `GenerationService`.
  - `requirements.txt`: bổ sung `python-multipart`, thay `llama-index-llms-dashscope` bằng `llama-index-llms-openai`, gỡ `moviepy`.
- **Phase 1 — pipeline mới:**
  - **Một lượt decode** bằng `ffmpeg` (qua `infra/media_demux.py`) thay thế chuỗi moviepy `VideoChunker` + `AudioExtractor`.
  - **PySceneDetect** (`infra/scene_detector.py`) thay cho vòng lặp pixel-diff trong `visual_processor.py`. Mỗi scene lưu một keyframe đại diện ở midpoint.
  - **Whisper chạy trên toàn bộ audio.wav** một lần duy nhất, không còn ghép timestamp theo chunk offset.
  - Loại bỏ phụ thuộc moviepy khỏi hot path; chỉ cần `ffmpeg` và `ffprobe` trong `PATH`.

## 1. Mô hình Phân lớp
- **Orchestration (`VideoOrchestrator`):** Điều phối luồng xử lý chính (Demux → Scene → Transcribe → Index → Generate).
- **Media Demux (`MediaDemuxer`):** Một lệnh `ffmpeg` để tách `audio.wav` (16 kHz mono) và sample frame 1 fps. Thêm `ffprobe` để lấy duration / fps / has_audio.
- **Scene Detection (`SceneDetector`):** Sử dụng PySceneDetect `ContentDetector` để xác định ranh giới scene; lưu keyframe đại diện cho mỗi scene bằng OpenCV `VideoCapture`.
- **Audio Processing (`TranscriptionService`):** Faster-Whisper xử lý toàn bộ audio.wav một lần (VAD bật sẵn). Không cần chunk.
- **Data & Retrieval (`RAGService`):** LlamaIndex + FAISS lưu transcript segment + keyframe metadata; embedding HuggingFace `all-MiniLM-L6-v2` được đăng ký global.
- **Generation (`GenerationService`):** Qwen qua 9router (OpenAI-compatible). Sinh tóm tắt Map-Reduce, đồng thời trích Flashcards / Quiz.

## 2. Luồng Tương tác (Interaction Flow)
1. **Giai đoạn 1 (Tự động):**
   1. Upload (streamed, size-capped) → `data/jobs/{uuid}/video.mp4`.
   2. `MediaDemuxer.run()` → `audio.wav` + `frames/`.
   3. `SceneDetector.detect()` → `keyframes/`.
   4. Whisper trên `audio.wav` → `segments[]` (timestamp toàn cục, không cần offset).
   5. `RAGService.build_index_from_segments(segments, keyframes)` → FAISS index.
   6. `GenerationService.generate_summary(...)` → summary + flashcards + quiz.
2. **Giai đoạn 2 (Hỏi đáp):**
   - User đặt câu hỏi → RAG retrieve top-k → Qwen trả lời kèm timestamp + (nếu có) keyframe liên quan.
3. **Giai đoạn 3 (Studio):**
   - Flashcards và Mini-test sẵn sàng ngay sau pipeline.

## 3. UI Integration (React Web UI)
- **3-panel layout:**
  - Source Panel: danh sách video, upload.
  - Chat Panel: trò chuyện với AI.
  - Studio Panel: tóm tắt, flashcards, quiz.

## 4. AI Model Stack

### 4.1 Bảng tổng quan

| Thành phần | Model / Service | Provider | Mục đích |
|-----------|-----------------|----------|----------|
| **Demux** | ffmpeg / ffprobe | Local (binary trong PATH) | Tách audio + frame một lượt |
| **Scene Detection** | PySceneDetect `ContentDetector` | Local (`scenedetect[opencv]`) | Phát hiện chuyển scene → keyframe |
| **Transcription** | `faster-whisper` (`small` mặc định) | Local | Speech-to-text |
| **Embedding** | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace | Vector hoá segment |
| **Vector Store** | FAISS qua LlamaIndex | Local | Lưu / truy vấn |
| **LLM** | Qwen (qua 9router, OpenAI-compatible) | Alibaba / 9router | Tóm tắt, Q&A, flashcards, quiz |

### 4.2 Sơ đồ luồng xử lý

```
Video MP4
  ↓
[MediaDemuxer]  (ffmpeg single pass)
  ├─ audio.wav (16 kHz mono PCM)
  └─ frames/   (1 fps JPEG sample)
  ↓
┌───────────────────────────────┬───────────────────────────────┐
│ [Whisper full-audio]          │ [SceneDetector] (PySceneDetect)│   (Phase 2: SONG SONG
│   └─ segments[]               │   └─ keyframes[] (midpoint/scene)│   qua ThreadPool)
└───────────────────────────────┴───────────────────────────────┘
  ↓
[RAGService.build_index_from_segments]
  └─ FAISS index (segment + keyframe metadata)
  ↓
[GenerationService] (Qwen Map-Reduce, Map chạy song song N=MAP_PHASE_CONCURRENCY)
  └─ Summary + Flashcards + Quiz
```

## 5. Biến môi trường mới (v0.4)

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `FRAME_SAMPLE_FPS` | `1.0` | Tốc độ sample frame của ffmpeg |
| `SCENE_THRESHOLD` | `27.0` | Ngưỡng `ContentDetector` |
| `MIN_SCENE_LEN_SEC` | `1.5` | Độ dài tối thiểu của scene (chống flicker) |
| `WHISPER_MODEL_SIZE` | `small` | tiny / base / small / medium / large-v3 |
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) | Giới hạn upload |
| `LOG_LEVEL` | `INFO` | Mức log của root logger |
| `CORS_ALLOWED_ORIGINS` | (xem code) | Danh sách origin, phẩy ngăn cách |
| `MAP_PHASE_CONCURRENCY` | `4` | Số call LLM song song trong Map phase (Phase 2) |
| `WHISPER_BEAM_SIZE` | `1` | Beam size của faster-whisper (Phase 3) |
| `WHISPER_VAD_MIN_SILENCE_MS` | `300` | VAD: ngưỡng im lặng tối thiểu để cắt (Phase 3) |
| `WHISPER_VAD_THRESHOLD` | `0.45` | VAD: ngưỡng phát hiện giọng nói (Phase 3) |
| `WHISPER_CPU_THREADS` | `0` | 0 = auto (`os.cpu_count()`) (Phase 3) |
| `WHISPER_NUM_WORKERS` | `2` | ctranslate2 pipeline workers (Phase 3) |
| `WHISPER_LANGUAGE` | *(auto)* | Pin ngôn ngữ, bỏ qua detect (Phase 3) |
| `WHISPER_MIN_CONFIDENCE` | `-1.0` | Drop segment có avg_logprob thấp; -1 = tắt (Phase 3) |

## 6. Yêu cầu hệ thống

- Python 3.9+
- Node.js 16+ (cho frontend)
- **`ffmpeg` và `ffprobe` phải có trong `PATH`** (Phase 1)
- 9router chạy tại `NINE_ROUTER_URL` (mặc định `http://localhost:20128/v1`)
