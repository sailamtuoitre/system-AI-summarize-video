# Quy trình Xử lý Kỹ thuật (v0.5 — Parallelism)

## 1. Giai đoạn Tiền xử lý (Demux)
- **`MediaDemuxer.run(video_path, job_dir)`** dùng một lệnh `ffmpeg` để xuất:
  - `audio.wav` — 16 kHz mono PCM `s16le` (Whisper-ready).
  - `frames/frame_*.jpg` — sample 1 fps, downscale `min(640, iw)` giữ tỉ lệ, JPEG `-q:v 3`.
- Trước đó `ffprobe` lấy `duration`, `fps`, `has_audio`, codec.
- Không còn cắt video thành chunk vật lý trên ổ đĩa → loại bỏ ~5 phút overhead so với pipeline cũ trên video 60 phút.

## 2 + 3. Phát hiện Scene ∥ Transcription (Phase 2: chạy song song)
Sau khi demux xong, orchestrator dùng `ThreadPoolExecutor(max_workers=2)` để chạy **đồng thời**:

- **`SceneDetector.detect(...)`** — `scenedetect.ContentDetector` (`threshold=27`, `min_scene_len=1.5s`); 1 keyframe / scene tại midpoint qua `cv2.VideoCapture` + `CAP_PROP_POS_MSEC`. Nếu video tĩnh → coi toàn bộ là 1 scene, lưu keyframe `t=0`.
- **`TranscriptionService.transcribe(audio.wav)`** — faster-whisper (Phase 3 tuning):
  - `beam_size=WHISPER_BEAM_SIZE` (mặc định 1, ~2× nhanh hơn beam=5).
  - VAD chặt hơn: `min_silence_duration_ms=300`, `threshold=0.45`.
  - `cpu_threads=auto` + `num_workers=2` cho ctranslate2 pipeline parallelism.
  - `language=WHISPER_LANGUAGE` để skip auto-detect (tiết kiệm 1-3s/file).
  - `condition_on_previous_text=False` để giảm hallucination loop.
  - Lọc segment có `avg_logprob < WHISPER_MIN_CONFIDENCE` (off mặc định).

Mỗi nhánh được bọc try/except riêng — nhánh fail trả về list rỗng để pipeline vẫn tiếp tục được. `latency.scene_detection` và `latency.transcription` được đo độc lập (đều bắt đầu cùng thời điểm khi vào ThreadPool).

Lý do dùng threads thay vì asyncio: cả ctranslate2 (faster-whisper) lẫn OpenCV/numpy (PySceneDetect) đều giải phóng GIL nên Python threads thực sự chạy song song; đồng thời giữ orchestrator API là sync, tương thích với FastAPI `BackgroundTasks`.

## 4. Giai đoạn Indexing (RAG)
- `RAGService.build_index_from_segments(segments, storage_path, keyframes)`:
  - Tạo `Document` cho từng segment, đính kèm `keyframes[]` (cửa sổ ±30s) vào metadata.
  - Nếu không có segment nhưng có keyframe (video không lời) → tạo Document từ keyframe.
  - Nếu cả hai đều rỗng → 1 Document placeholder để index không lỗi.
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace, lazy-loaded, đăng ký vào `Settings.embed_model`).
- Vector store: FAISS (qua LlamaIndex `VectorStoreIndex`), persist xuống `index/`.

## 5. Giai đoạn Tóm tắt (Map-Reduce, Phase 2: Map song song)
- **Map:** Chia `top_k=30` retrieved nodes thành cụm 15 node, gửi mỗi cụm tới Qwen yêu cầu JSON `{summary, flashcards, quiz}`. Các call **chạy song song qua `ThreadPoolExecutor`**, giới hạn bởi `MAP_PHASE_CONCURRENCY` (mặc định 4).
- Tóm tắt từng đoạn được gom vào `all_partials[idx]` theo đúng thứ tự gốc bất kể thứ tự hoàn tất → Reduce nhận được context theo thời gian video.
- Flashcard/quiz có trường thiếu được skip với log warning thay vì crash chunk.
- **Reduce:** Tổng hợp các bản tóm tắt nhỏ thành 200–300 từ tiếng Việt (vẫn 1 call duy nhất, sau khi Map xong).

## 6. Giai đoạn Truy vấn (Q&A)
- `/job/{id}/chat` → `_validate_job_id` (UUID) → `RAGService.load_index` → `query(top_k=5)` → `GenerationService.answer_question`.
- Trả về `{ answer, sources: [mm:ss, ...] }`.

## 7. Tracking Hiệu suất
`JobState.latency` ghi nhận từng giai đoạn (key mới ở v0.4):

| Key | Ý nghĩa |
|-----|---------|
| `demux` | Thời gian `MediaDemuxer.run` |
| `scene_detection` | Thời gian `SceneDetector.detect` |
| `transcription` | Thời gian Whisper trên full audio |
| `indexing` | Thời gian build FAISS |
| `generation` | Thời gian Qwen Map-Reduce + materials (Map song song theo `MAP_PHASE_CONCURRENCY`) |

## 8. Lộ trình tối ưu (đề xuất tiếp theo)
- ✅ **Phase 3 — Whisper tuning** (đã làm v0.6): beam=1, VAD chặt hơn, threads/workers, language pin, confidence filter.
- **Stage T** — phân loại video qua transcript (deixis keywords) để tắt visual extraction khi không cần.
- **Stage C** — gate per-keyframe: phash dedup, brightness sanity, OCR length.
- **Per-stage checkpoint** — lưu `audio.wav`, `segments.json`, `scenes.json`, `index/` để resume khi crash.
- **Cluster-based summary + structured JSON output:** giảm token + loại bỏ regex parse JSON.
