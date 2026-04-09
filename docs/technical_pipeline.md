# Quy trình Xử lý Kỹ thuật (v0.3 - Long Video & Multi-modal)

## 1. Giai đoạn Tiền xử lý (Preprocessing)
- **Audio Extraction:** Tách audio và chia nhỏ (chunking) nếu video > 30 phút để tránh quá tải RAM.
- **Keyframe Extraction:** OpenCV quét video mỗi giây, chụp ảnh (keyframes) tại các mốc thời gian có sự thay đổi hình ảnh lớn (> 50% pixel đổi màu) - thường là lúc chuyển slide.

## 2. Giai đoạn Nhận dạng (Recognition)
- **Transcription:** `faster-whisper` xử lý từng audio chunk và gộp lại thành transcript dài hoàn chỉnh.
- **Visual OCR (Option):** Trích xuất text từ các keyframes để lấy nội dung slide (tiêu đề, công thức, mã nguồn).

## 3. Giai đoạn Tóm tắt (Summarization - Map-Reduce)
- **Map Phase:** Qwen2.5-VL-Plus nhận từng cụm ~15 nodes (7-10 phút) để trích xuất 5 ý chính.
- **Reduce Phase:** Qwen tổng hợp toàn bộ các ý chính để viết bản tóm tắt học thuật (150-250 từ).

## 4. Giai đoạn Truy vấn (RAG & Q&A)
- **Indexing:** LlamaIndex lưu trữ dữ liệu đa phương thức.
- **Q&A:** Qwen trả lời câu hỏi người dùng. Nếu câu trả lời nằm ở một slide cụ thể, hệ thống sẽ hiển thị keyframe tương ứng để làm bằng chứng trực quan.

## 5. Tối ưu hóa Hiệu suất
- **Memory Management:** Giải phóng bộ nhớ model Whisper sau khi transcribe xong để dành tài nguyên cho Qwen.
- **Parallelism:** Chạy song song việc tách audio và trích xuất keyframes để giảm 30% thời gian chờ.
