# Kiến trúc Hệ thống: Multi-modal RAG Pipeline (v0.3)

## 1. Mô hình Phân lớp
- **Orchestration (Custom Pattern):** Điều phối luồng xử lý chính (Video -> Audio/Visual -> Transcribe/OCR -> Index -> Summary) thông qua `VideoOrchestrator`.
- **Visual Processing (OpenCV):** Trích xuất các khung hình chính (keyframes) khi giáo viên chuyển slide. Phát hiện thay đổi nội dung màn hình để chụp ảnh minh họa.
- **Audio Processing (Faster-Whisper):** Chuyển giọng nói thành văn bản có timestamp. Hỗ trợ chia nhỏ (chunking) audio cho video dài (> 60 phút).
- **Data & Retrieval (LlamaIndex):** Lưu trữ transcript, OCR text và metadata hình ảnh để thực hiện truy vấn RAG đa phương thức.
- **Generation (Alibaba Qwen):** Sử dụng model **Qwen2.5-VL-Plus** để xử lý tóm tắt (Map-Reduce), hiểu hình ảnh slide và trả lời câu hỏi thông minh.

## 2. Luồng Tương tác (Interaction Flow)
1. **Giai đoạn 1 (Tự động - Multi-modal):**
   - Upload -> Extract Audio & Keyframes.
   - Transcribe (Whisper) & OCR (Chữ trên slide).
   - Gemini sinh Summary (Map-Reduce) dựa trên cả lời nói và hình ảnh.
2. **Giai đoạn 2 (Hỏi đáp):**
   - Người dùng đặt câu hỏi.
   - RAGService tìm kiếm thông tin liên quan từ cả transcript và nội dung slide.
   - Qwen trả lời kèm bằng chứng timestamp và hình ảnh slide liên quan.
3. **Giai đoạn 3 (Nâng cao - Manual):**
   - Click "Tạo Flashcards/Mini-test" -> Qwen sinh nội dung dựa trên toàn bộ context video.

## 3. UI Integration (React Web UI)
- **3-panel layout:** 
  - Source Panel: Danh sách video và upload.
  - Chat Panel: Trò chuyện với AI (hiển thị ảnh slide nếu cần).
  - Studio Panel: Hiển thị tóm tắt, flashcards và quiz.

## 4. AI Model Stack

### 4.1 Bảng tổng quan các model

| Thành phần | Model/Service | Provider | Mục đích |
|-----------|---------------|----------|----------|
| **Transcription** | `faster-whisper` | OpenAI (local) | Chuyển giọng nói thành văn bản |
| **Visual Analysis**| `OpenCV` | Local | Trích xuất keyframes (slide changes) |
| **LLM & Vision** | **Qwen2.5-VL-Plus** | Alibaba | Model chính: Hiểu video, tóm tắt, Q&A |
| **Vector Store** | `VectorStoreIndex` | LlamaIndex | Lưu trữ và truy vấn tri thức video |

### 4.2 Sơ đồ luồng xử lý (Long Video Optimized)

```
Video MP4 (> 60 mins)
  ↓ (Split: Audio & Keyframes)
[Audio] → Chunking → Faster-Whisper → Sub-transcripts
[Visual] → OpenCV Keyframes → OCR → Slide Texts
  ↓
Merged Context (Transcript + Slide Text + Image Metadata)
  ↓
Qwen Map Phase (Tóm tắt từng đoạn 10 phút)
  ↓
Qwen Reduce Phase (Tổng hợp bản tóm tắt cuối cùng)
  ↓
Vector Index (LlamaIndex) → Phục vụ Chat & Studio
```
