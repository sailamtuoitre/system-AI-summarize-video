# Đặc tả Dữ liệu: Interactive & On-Demand (v0.3)

## Cập nhật v0.3
- Thêm trường `filename` vào JobState
- Tích hợp `source_node_id` vào tất cả Evidence objects
- Cập nhật Chat API sang dùng request body
- Bổ sung visual evidence metadata trong RAG nodes
- Thêm CORS configuration cho localhost

## 1. Chat History Schema
Lịch sử chat được quản lý bởi UI session state (React `useState`).

```json
{
  "chat_history": [
    {"role": "user", "content": "Thuật ngữ A nghĩa là gì?"},
    {"role": "assistant", "content": "Thuật ngữ A nghĩa là..., được nhắc tới ở phút 02:45.", "source_nodes": ["uuid-1"]}
  ]
}
```

## 2. On-Demand Status
Mở rộng `job_state.json` để quản lý việc các tính năng phụ đã được khởi tạo hay chưa.

```json
{
  "job_id": "...",
  "filename": "Bai_giang_Toan.mp4",
  "video_path": "./data/jobs/<job_id>/video.mp4",
  "status": "completed",
  "features": {
    "summary": "ready",
    "chat": "ready",
    "flashcards": "ready",
    "mini_test": "ready"
  }
}
```

### 2.1 JobState Schema (Updated v0.3)

| Trường | Kiểu | Mô tả |
|-------|------|-------|
| `job_id` | string | UUID duy nhất cho mỗi job |
| `filename` | string | Tên file video gốc (mới thêm v0.3) |
| `video_path` | string | Đường dẫn tới file video đã lưu |
| `status` | enum | Trạng thái: pending, extracting_audio, transcribing, indexing, generating_summary, completed, failed |
| `features` | object | Trạng thái các tính năng: not_started, processing, ready, failed |
| `summary` | object | Kết quả tóm tắt (SummaryOutput) |
| `flashcards` | array | Danh sách flashcards |
| `quiz` | array | Danh sách câu hỏi trắc nghiệm |

## 2.2 Chat API Request/Response (Updated v0.3)

### Request (POST /job/{job_id}/chat)
```json
{
  "question": "Thuật ngữ A nghĩa là gì?"
}
```

### Response
```json
{
  "answer": "Thuật ngữ A nghĩa là..., được nhắc tới ở phút 02:45.",
  "sources": ["02:45", "03:10"]
}
```

## 2.3 CORS Configuration (v0.3)
- Allowed origins: `http://localhost:3000`, `http://localhost:5173`
- Methods: All
- Headers: All

## 3. Metadata của Node (Cập nhật v0.3 - Thêm Visual Evidence)
Bổ sung metadata cho visual evidence tích hợp keyframes.

```json
{
  "node_id": "uuid-1",
  "start_time": "00:00",
  "end_time": "00:05",
  "timestamp_mmss": "00:00",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "has_visual_evidence": true,
  "keyframes": [
    {"path": "./keyframes/keyframe_00_02.jpg", "timestamp": 2.0, "time_str": "00:02"}
  ],
  "similarity_score": 0.87
}
```

| Trường | Kiểu | Mô tả |
|-------|------|-------|
| `node_id` | string | UUID duy nhất cho mỗi node trong vector index |
| `start_time` | float | Thời gian bắt đầu (giây) |
| `end_time` | float | Thời gian kết thúc (giây) |
| `timestamp_mmss` | string | Mốc thời gian dùng để trích dẫn (mm:ss) |
| `segment_id` | string | ID của segment từ Whisper |
| `has_visual_evidence` | boolean | Có keyframe liên quan không (mới v0.3) |
| `keyframes` | array | Danh sách keyframes trong vòng 30s (mới v0.3) |
| `embedding_model` | string | Model embedding đã sử dụng |
| `similarity_score` | float | Điểm tương đồng khi retrieve (cosine similarity) |

## 4. Kết quả Tóm tắt (Initial Summary)
```json
{
  "initial_summary": "Đoạn văn bản tóm tắt tổng thể nội dung video..."
}
```

## 5. Model Configuration & Metadata

### 5.1 Metadata của Transcript Segment (từ faster-whisper)
```json
{
  "segment_id": "uuid",
  "start": 0.0,
  "end": 5.2,
  "text": "Nội dung transcript của đoạn audio...",
  "confidence": 0.95
}
```

| Trường | Kiểu | Mô tả |
|-------|------|-------|
| `segment_id` | string | UUID duy nhất cho mỗi segment |
| `start` | float | Thời gian bắt đầu (giây) |
| `end` | float | Thời gian kết thúc (giây) |
| `text` | string | Nội dung transcript |
| `confidence` | float | Độ tin cậy của model (0.0 - 1.0) |

### 5.2 Metadata của Vector Node (trong LlamaIndex)
```json
{
  "node_id": "uuid-1",
  "start_time": "00:00",
  "end_time": "00:05",
  "timestamp_mmss": "00:00",
  "embedding_model": "all-MiniLM-L6-v2",
  "similarity_score": 0.87
}
```

| Trường | Kiểu | Mô tả |
|-------|------|-------|
| `node_id` | string | UUID duy nhất cho mỗi node trong vector index |
| `start_time` | string | Thời gian bắt đầu (định dạng mm:ss) |
| `end_time` | string | Thời gian kết thúc (định dạng mm:ss) |
| `timestamp_mmss` | string | Mốc thời gian dùng để trích dẫn |
| `embedding_model` | string | Model embedding đã sử dụng |
| `similarity_score` | float | Điểm tương đồng khi retrieve (cosine similarity) |

### 5.3 Model Configuration Schema (Updated v0.3)
Cấu hình các model sử dụng trong hệ thống:

```json
{
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
    "chunk_overlap": 20
  },
  "llm": {
    "model": "qwen-3.6-plus",
    "provider": "alibaba-dashscope",
    "temperature": 0.7,
    "multimodal": true
  },
  "visual": {
    "provider": "opencv",
    "diff_threshold": 0.5,
    "keyframe_interval": 1.0
  },
  "retrieval": {
    "top_k": 5,
    "vector_store": "faiss",
    "similarity_metric": "cosine",
    "visual_evidence": true
  }
}
```

### 5.4 Flashcard Output Schema
```json
{
  "front": "Khái niệm hoặc câu hỏi ngắn",
  "back": "Giải thích chi tiết",
  "latex": "$$E = mc^2$$",
  "evidence": {
    "timestamp": "02:45",
    "quote": "Câu trích dẫn nguyên văn từ video...",
    "source_node_id": "uuid-1"
  }
}
```

### 5.5 Quiz Question Output Schema
```json
{
  "question": "Câu hỏi rõ ràng dựa trên nội dung video",
  "options": ["A. Phương án A", "B. Phương án B", "C. Phương án C", "D. Phương án D"],
  "answer": "B. Phương án B",
  "explanation": "Giải thích ngắn gọn tại sao đáp án này đúng",
  "evidence": {
    "timestamp": "03:20",
    "quote": "Câu trích dẫn chứng minh từ video...",
    "source_node_id": "uuid-2"
  }
}
```
