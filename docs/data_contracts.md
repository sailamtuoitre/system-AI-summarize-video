# Đặc tả Dữ liệu (v0.5)

## Cập nhật v0.5 (Phase 2)
- `latency.scene_detection` và `latency.transcription` giờ **chạy song song** — tổng wall-clock của 2 giai đoạn này ≈ `max(scene_detection, transcription)`, không phải tổng cộng.
- `latency.generation` rút ngắn rõ rệt cho video dài do Map phase chạy song song theo `MAP_PHASE_CONCURRENCY`.
- Không thay đổi schema field nào.

## Cập nhật v0.4
- Pydantic v2: `QuizQuestion.options` dùng `min_length=4, max_length=4` (thay `min_items`/`max_items`).
- `JobState.latency` có thêm các key giai đoạn mới: `demux`, `scene_detection`, `transcription`, `indexing`, `generation`.
- Endpoint per-job validate `job_id` là UUID; sai format trả `400`.
- Upload streamed, vượt `MAX_UPLOAD_BYTES` trả `413`.
- Embedding global đăng ký vào `Settings.embed_model` của LlamaIndex để tránh fallback OpenAI.
- LLM client dùng `llama-index-llms-openai` (OpenAI-compatible, trỏ tới 9router qua `base_url`).

## 1. Chat History (UI session state)
```json
{
  "chat_history": [
    {"role": "user",      "content": "Thuật ngữ A nghĩa là gì?"},
    {"role": "assistant", "content": "Thuật ngữ A nghĩa là..., được nhắc tới ở phút 02:45.", "source_nodes": ["uuid-1"]}
  ]
}
```

## 2. JobState Schema
```json
{
  "job_id": "uuid",
  "filename": "Bai_giang_Toan.mp4",
  "video_path": "./data/jobs/<uuid>/video.mp4",
  "status": "completed",
  "created_at": "2026-04-25T12:00:00",
  "completed_at": "2026-04-25T12:18:30",
  "features": {
    "summary": "ready",
    "chat": "ready",
    "flashcards": "ready",
    "mini_test": "ready"
  },
  "summary": { "initial_summary": "..." },
  "flashcards": [],
  "quiz": [],
  "chunk_progress": {
    "chunk_duration_seconds": 180,
    "total_chunks": 0,
    "processed_chunks": 0
  },
  "latency": {
    "demux": 28.4,
    "scene_detection": 12.7,
    "transcription": 540.1,
    "indexing": 31.0,
    "generation": 95.6
  },
  "error_message": null
}
```

> Ghi chú v0.4: `chunk_progress` được giữ trong schema để giữ tương thích frontend, nhưng pipeline mới không dùng (Whisper chạy full-audio). Có thể coi như deprecated, sẽ bị bỏ ở v0.5.

### 2.1 Bảng trường

| Trường | Kiểu | Mô tả |
|-------|------|-------|
| `job_id` | string (UUID) | Định danh job |
| `filename` | string | Tên file gốc |
| `video_path` | string | Đường dẫn lưu video |
| `status` | enum | `pending` / `extracting_audio` / `transcribing` / `indexing` / `generating_summary` / `completed` / `failed` |
| `features` | object | Trạng thái: `not_started` / `processing` / `ready` / `failed` |
| `summary` | object | `SummaryOutput` |
| `flashcards` | array | Mảng `Flashcard` |
| `quiz` | array | Mảng `QuizQuestion` |
| `latency` | object | Thời gian (giây) cho từng giai đoạn |
| `chunk_progress` | object | _Deprecated v0.4_, giữ cho tương thích |
| `error_message` | string \| null | Thông báo lỗi nếu `status=failed` |

## 3. API

### 3.1 POST `/upload`
- `multipart/form-data` với field `file` (.mp4).
- Streamed; vượt `MAX_UPLOAD_BYTES` → `413`.
- Response: `{ "job_id": "uuid", "status": "pending" }`.

### 3.2 GET `/job/{job_id}`
- `job_id` phải là UUID hợp lệ; sai format → `400 "job_id khong hop le"`.
- Trả về `JobState`.

### 3.3 POST `/job/{job_id}/feature/{feature_name}`
- `feature_name` ∈ `{ "flashcards", "mini_test" }`.
- `job_id` phải là UUID hợp lệ.

### 3.4 POST `/job/{job_id}/chat`
- Request body:
```json
{ "question": "Thuật ngữ A nghĩa là gì?" }
```
- Response:
```json
{
  "answer": "Thuật ngữ A nghĩa là..., được nhắc tới ở phút 02:45.",
  "sources": ["02:45", "03:10"]
}
```
- `409` nếu index của video chưa sẵn sàng.

## 4. CORS
- Origins mặc định: `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:3001`, `http://127.0.0.1:3001`, `http://localhost:5173`, `http://127.0.0.1:5173`.
- Có thể override qua `CORS_ALLOWED_ORIGINS` (phẩy ngăn cách).

## 5. Vector Node Metadata (RAG)
```json
{
  "node_id": "uuid",
  "start_time": 0.0,
  "end_time": 5.2,
  "timestamp_mmss": "00:00",
  "segment_id": "segment_0",
  "chunk_index": null,
  "chunk_id": null,
  "has_visual_evidence": true,
  "keyframes": [
    {
      "scene_index": 0,
      "start": 0.0,
      "end": 12.4,
      "timestamp": 6.2,
      "time_str": "00:06",
      "path": "./data/jobs/<id>/keyframes/scene_0000_000006s.jpg"
    }
  ],
  "similarity_score": 0.87
}
```

> Ghi chú v0.4: `chunk_index` / `chunk_id` luôn `null` ở pipeline mới (không còn cắt chunk vật lý). Giữ trường để tương thích ngược.

## 6. Whisper Segment
```json
{
  "id": 0,
  "start": 0.0,
  "end": 5.2,
  "text": "Nội dung transcript...",
  "confidence": -0.18
}
```

## 7. Keyframe Schema (output `SceneDetector.detect`)
```json
{
  "scene_index": 0,
  "start": 0.0,
  "end": 12.4,
  "timestamp": 6.2,
  "time_str": "00:06",
  "path": "./data/jobs/<id>/keyframes/scene_0000_000006s.jpg"
}
```

## 8. Model Configuration (v0.4)
```json
{
  "demux": {
    "tool": "ffmpeg",
    "audio_sample_rate": 16000,
    "audio_codec": "pcm_s16le",
    "frame_fps": 1.0,
    "frame_max_width": 640,
    "frame_quality": 3
  },
  "scene_detection": {
    "library": "scenedetect",
    "detector": "ContentDetector",
    "threshold": 27.0,
    "min_scene_len_sec": 1.5
  },
  "transcription": {
    "model": "small",
    "provider": "faster-whisper",
    "compute_type": "int8",
    "device": "cpu",
    "vad_filter": true,
    "beam_size": 5
  },
  "embedding": {
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "provider": "huggingface",
    "dimensions": 384,
    "chunk_size": 200,
    "chunk_overlap": 20,
    "registered_globally": true
  },
  "llm": {
    "model": "qwen-3.6-plus",
    "provider": "qwen-via-9router (OpenAI-compatible)",
    "base_url": "${NINE_ROUTER_URL}",
    "client_lib": "llama-index-llms-openai"
  },
  "retrieval": {
    "top_k": 5,
    "vector_store": "faiss",
    "similarity_metric": "cosine",
    "visual_evidence": true
  },
  "upload": {
    "max_bytes": 524288000,
    "streamed": true,
    "extension_whitelist": [".mp4"]
  },
  "parallelism": {
    "scene_and_transcribe": "ThreadPoolExecutor(max_workers=2)",
    "map_phase_concurrency": 4,
    "map_phase_concurrency_env": "MAP_PHASE_CONCURRENCY"
  }
}
```

## 9. Flashcard Schema
```json
{
  "front": "Khái niệm hoặc câu hỏi ngắn",
  "back": "Giải thích chi tiết",
  "latex": "$$E = mc^2$$",
  "evidence": {
    "timestamp": "02:45",
    "quote": "Câu trích dẫn nguyên văn...",
    "source_node_id": "uuid-1"
  }
}
```

## 10. QuizQuestion Schema
```json
{
  "question": "Câu hỏi rõ ràng dựa trên nội dung video",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "answer": "B. ...",
  "explanation": "Giải thích ngắn gọn",
  "evidence": {
    "timestamp": "03:20",
    "quote": "Câu trích dẫn chứng minh...",
    "source_node_id": "uuid-2"
  }
}
```
> v0.4: `options` dùng `min_length=4, max_length=4` (pydantic v2).
