# Tổng quan Dự án: MVP AI Video Assistant (v0.3)

## Cập nhật v0.3
- Tự động hóa tạo Flashcards/Quiz trong pipeline (tiết kiệm thời gian)
- Tích hợp visual evidence từ keyframes vào RAG
- Cải thiện bảo mật CORS (localhost only)
- Cải thiện UX: Job status hiển thị chi tiết, reset quiz không reload
- Đồng bộ phiên bản tài liệu lên v0.3

## 1. Giới thiệu
Công cụ hỗ trợ học tập thông minh dựa trên video bài giảng. Hệ thống sử dụng AI đa phương thức để "xem", "nghe" và "hiểu" nội dung video dài, giúp sinh viên ôn tập nhanh chóng.

## 2. Mục tiêu chính
- Xử lý ổn định video bài giảng dài (trên 1 tiếng).
- Kết hợp lời giảng (audio) và slide bài giảng (image) để tóm tắt chính xác nhất.
- Cung cấp chatbot Q&A có khả năng trích dẫn cả lời nói và hình ảnh slide.

## 3. Phạm vi MVP (Cập nhật v0.3)
- **Input:** Video MP4 (không giới hạn độ dài, khuyến nghị < 120 phút).
- **Tính năng cốt lõi (Tự động):**
    - **Multi-modal Summary:** Tóm tắt kết hợp Transcript và OCR Slide.
    - **Long Video Handling:** Kỹ thuật Map-Reduce giúp tóm tắt video dài mà không mất ý.
    - **Visual Evidence:** Chụp lại ảnh slide bài giảng liên quan đến câu trả lời.
    - **Auto Flashcards:** Tự động sinh 5-10 thẻ ghi nhớ trong pipeline.
    - **Auto Mini-test:** Tự động sinh câu hỏi trắc nghiệm kiểm tra kiến thức.
- **Tính năng tương tác:**
    - **Chat Q&A:** Hỏi đáp với AI, có trích dẫn timestamp và visual evidence.
    - **Studio Panel:** Xem tóm tắt, flashcards và quiz (đã sẵn sàng).

## 5. Công nghệ AI sử dụng

### 5.1 Các model chính

| Model | Provider | Vai trò |
|-------|----------|---------|
| **faster-whisper** | OpenAI (local) | Chuyển giọng nói thành văn bản chính xác |
| **OpenCV** | Local | Tự động chụp ảnh khi slide thay đổi |
| **Qwen2.5-VL-Plus** | Alibaba | LLM đa phương thức (Hiểu cả văn bản và hình ảnh) |

### 5.2 Kỹ thuật xử lý Video dài
Hệ thống áp dụng phương pháp **Map-Reduce Summarization**:
1. **Map:** Chia video thành các đoạn 10-15 phút, tóm tắt ý chính từng đoạn.
2. **Reduce:** Tổng hợp toàn bộ các bản tóm tắt nhỏ thành một bức tranh toàn cảnh của bài giảng.

## 6. Giao diện người dùng (UI)
Sử dụng giao diện **React Web App (`apps/web-ui`)** chạy tại cổng 3000 (mặc định Vite).
- Layout 3 khung hình chuyên nghiệp.
- Hỗ trợ xem nhiều video bài giảng song song.
