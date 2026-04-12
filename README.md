# 🎓 AI Video Assistant - Smart Learning Platform

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Một nền tảng học tập thông minh sử dụng AI đa phương thức để phân tích video bài giảng, giúp sinh viên ôn tập nhanh chóng và hiệu quả hơn.

## ✨ Tính năng chính

### 🎯 Tự động xử lý video
- **Multi-modal Processing:** Kết hợp âm thanh (audio) và hình ảnh (slides) để hiểu nội dung
- **Map-Reduce Summarization:** Kỹ thuật tóm tắt thông minh cho video dài (>60 phút)
- **Visual Evidence:** Tự động chụp keyframes khi slide thay đổi, cung cấp bằng chứng hình ảnh
- **Auto Flashcards & Quiz:** Tạo tự động thẻ ghi nhớ và câu hỏi trắc nghiệm ngay trong pipeline

### 💬 Thông minh & Tương tác
- **AI Chatbot:** Hỏi đáp về nội dung video với trích dẫn timestamp chính xác
- **RAG (Retrieval-Augmented Generation):** Tìm kiếm thông tin từ vector database trước khi sinh câu trả lời
- **Visual Context:** Câu trả lời có kèm theo hình ảnh slide liên quan

### 🎨 Giao diện hiện đại
- **3-Panel Layout:** Source (video list) | Chat | Studio (summary, flashcards, quiz)
- **Real-time Status:** Hiển thị chi tiết trạng thái xử lý từng giai đoạn
- **Responsive Design:** Thiết kế tối ưu cho cả desktop và tablet

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                      UI (React + Vite)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ SourcePanel │  │  ChatPanel   │  │   StudioPanel    │   │
│  │  (Upload &  │  │  (AI Q&A +   │  │ (Summary, Cards, │   │
│  │   Videos)   │  │   Flashcards)│  │      Quiz)       │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/REST API
┌───────────────────────────▼─────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               VideoOrchestrator                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │  Audio   │  │  Visual  │  │   Transcription  │   │   │
│  │  │Extractor │  │Processor │  │   (Whisper)      │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │   RAG    │  │Generation│  │    JobManager    │   │   │
│  │  │ Service  │  │ (Qwen)   │  │  (State Mgmt)    │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  FAISS Index │  │  Keyframes   │  │   Job States     │   │
│  │  (Vectors)   │  │   (Images)   │  │    (JSON)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Công nghệ sử dụng

### AI/ML Stack
| Thành phần | Công nghệ | Mục đích |
|-----------|-----------|----------|
| **Transcription** | Faster-Whisper (small) | Chuyển giọng nói thành văn bản |
| **Visual Processing** | OpenCV | Trích xuất keyframes từ video |
| **LLM** | **Qwen-3.6-Plus** (Alibaba DashScope) | Model chính: Tóm tắt, Q&A, sinh nội dung |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | Vector hóa văn bản |
| **Vector Store** | FAISS + LlamaIndex | Lưu trữ và truy xuất thông tin |

### Backend
- **Framework:** FastAPI (Python 3.9+)
- **Architecture:** Service-oriented, Dependency Injection
- **Job Management:** File-based state tracking (JSON)

### Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** CSS-in-JS với custom design system

## 📦 Cài đặt

### Yêu cầu hệ thống
- Python 3.9 trở lên
- Node.js 16+ và npm
- 4GB RAM tối thiểu (khuyến nghị 8GB)
- DashScope API key (từ Alibaba Cloud)

### 1. Clone repository
```bash
git clone <repository-url>
cd "CDIO 3"
```

### 2. Cài đặt Backend
```bash
# Cài đặt Python dependencies
pip install -r requirements.txt

# Tạo file cấu hình môi trường
cp .env.example .env

# Chỉnh sửa .env và thêm DashScope API key của bạn
# DASHSCOPE_API_KEY=your_api_key_here
```

### 3. Cài đặt Frontend
```bash
cd apps/web-ui
npm install
```

### 4. Chạy ứng dụng

**Terminal 1 - Backend API:**
```bash
cd apps/api
python main.py
# API sẽ chạy tại: http://localhost:8000
```

**Terminal 2 - Frontend UI:**
```bash
cd apps/web-ui
npm run dev
# UI sẽ chạy tại: http://localhost:5173
```

## 🚀 Sử dụng

1. **Upload video:** Kéo thả hoặc click để tải lên file MP4
2. **Đợi xử lý:** Hệ thống tự động:
   - Trích xuất âm thanh và keyframes
   - Chuyển giọng thành văn bản (Whisper)
   - Xây dựng vector index với visual evidence
   - Tạo tóm tắt, flashcards và quiz tự động
3. **Hỏi đáp:** Chat với AI về nội dung video
4. **Ôn tập:** Xem flashcards và làm mini-test trong Studio Panel

## 📁 Cấu trúc dự án

```
CDIO 3/
├── apps/
│   ├── api/              # FastAPI backend
│   │   └── main.py       # Entry point
│   └── web-ui/           # React frontend
│       └── src/components/
├── core/
│   ├── domain/           # Data models & schemas
│   │   └── models.py
│   └── services/         # Business logic
│       ├── orchestrator.py
│       ├── generation_service.py
│       ├── rag_service.py
│       ├── transcription_service.py
│       └── job_manager.py
├── infra/
│   ├── audio_extractor.py
│   └── visual_processor.py
├── data/
│   └── jobs/             # Job storage (auto-created)
└── docs/
    ├── architecture.md
    ├── data_contracts.md
    └── project_overview.md
```

## 🔧 Cấu hình

Tất cả cấu hình nằm trong file `.env`:

```env
# AI Configuration
DASHSCOPE_API_KEY=your_api_key_here
QWEN_MODEL_NAME=qwen-3.6-plus

# Storage Paths
DATA_DIR=./data
JOBS_DIR=./data/jobs

# Server
PORT=8000
HOST=0.0.0.0

# Feature Flags
ENABLE_VISUAL_PROCESSING=true
ENABLE_MAP_REDUCE=true
```

## 📊 Luồng xử lý chi tiết

### Pipeline tự động (Upload → Completed)

```
1. Upload Video (.mp4)
   ↓
2. Extract Audio (.wav) + Keyframes (images)
   ↓
3. Transcribe Audio → Segments (Whisper)
   ↓
4. Build RAG Index (FAISS) với keyframe metadata
   ↓
5. Generate Summary (Map-Reduce với Qwen)
   ↓
6. Auto-create Flashcards & Quiz
   ↓
7. Mark as COMPLETED
```

### Chat Q&A Flow

```
User Question
   ↓
Retrieve Top-K similar nodes (FAISS)
   ↓
Build context with visual evidence
   ↓
Qwen generates answer with citations
   ↓
Return answer + timestamps + keyframe refs
```

## 🔒 Bảo mật

- **CORS:** Cấu hình cho localhost only (`http://localhost:3000`, `http://localhost:5173`)
- **API Keys:** Lưu trong `.env`, không commit lên Git
- **Data Isolation:** Mỗi job có thư mục riêng

## 🐛 Xử lý sự cố

### Lỗi thường gặp

**1. "DashScope API Key not found"**
- Kiểm tra file `.env` đã có `DASHSCOPE_API_KEY` hợp lệ

**2. "Port 8000 already in use"**
- Thay đổi `PORT` trong `.env` hoặc dừng ứng dụng khác

**3. "Out of memory" với video dài**
- Giảm `diff_threshold` trong `visual_processor.py`
- Hoặc tăng RAM/swap space

## 📝 Tài liệu chi tiết

- [Architecture Documentation](docs/architecture.md)
- [Data Contracts & Schemas](docs/data_contracts.md)
- [Project Overview](docs/project_overview.md)

## 🗺️ Lộ trình phát triển

### v0.4 (Planned)
- [ ] Support cho multiple video formats (avi, mkv)
- [ ] Export flashcards/quiz sang PDF
- [ ] User authentication & accounts
- [ ] Progress tracking bar chi tiết

### v0.5 (Future)
- [ ] Multi-language support (English, Chinese)
- [ ] Real-time transcription streaming
- [ ] Collaborative study groups
- [ ] Mobile app (React Native)

## 👥 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng:
1. Fork repository
2. Tạo feature branch
3. Commit thay đổi
4. Push và tạo Pull Request

## 📄 License

MIT License - Xem [LICENSE](LICENSE) để biết chi tiết.

## 🙏 Cảm ơn

- **Alibaba Cloud** cho DashScope API và Qwen models
- **OpenAI** cho Whisper transcription technology
- **LlamaIndex** cho RAG framework
- **React & FastAPI communities**

---

<p align="center">Made with ❤️ for better learning experiences</p>
