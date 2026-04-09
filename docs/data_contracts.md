# Đặc tả Dữ liệu: Interactive & On-Demand (v0.2)

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
  "status": "completed",
  "features": {
    "summary": "ready",
    "chat": "ready",
    "flashcards": "not_started | processing | ready",
    "mini_test": "not_started | processing | ready"
  }
}
```

## 3. Metadata của Node (Không đổi)
Vẫn giữ nguyên các metadata: `start_time`, `end_time`, `timestamp_mmss`, `node_id`.

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

### 5.3 Model Configuration Schema
Cấu hình các model sử dụng trong hệ thống:

```json
{
  "transcription": {
    "model": "medium",
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
    "model": "models/gemini-1.5-flash",
    "provider": "google",
    "temperature": 0.7
  },
  "retrieval": {
    "top_k": 5,
    "vector_store": "faiss",
    "similarity_metric": "cosine"
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
