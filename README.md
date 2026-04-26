# AI Video Assistant - Smart Learning Platform (9router Optimized)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![9router](https://img.shields.io/badge/Router-9router-orange.svg)](https://9router.com)

Mot nen tang hoc tap thong minh su dung AI da phuong thuc de phan tich video bai giang, giup sinh vien on tap nhanh chong va hieu qua hon. Du an duoc toi uu hoa de su dung Qwen API thong qua 9router.

## Tinh nang chinh

### Tu dong xu ly video
- Multi-modal Processing: ket hop audio va slides de hieu noi dung.
- Map-Reduce Summarization: tom tat thong minh cho video dai.
- Visual Evidence: tu dong chup keyframes khi slide thay doi.
- Auto Flashcards & Quiz: tao the ghi nho va cau hoi trac nghiem trong pipeline.

### Thong minh va tuong tac
- AI Chatbot (Qwen Powered): hoi dap ve noi dung video voi timestamp.
- RAG: truy xuat thong tin tu vector database truoc khi sinh cau tra loi.
- 9router Integration: toi uu fallback va chi phi API.

### Giao dien hien dai
- 3-panel layout: Source | Chat | Studio.
- Real-time status cho tung giai doan xu ly.

## Kien truc he thong

```text
UI (React + Vite)        -> http://localhost:5173
Backend (FastAPI)        -> http://localhost:8000
9router (Smart Router)   -> http://localhost:20128
```

## Cong nghe su dung (v0.4)

| Thanh phan | Cong nghe | Muc dich |
| --- | --- | --- |
| Demux | ffmpeg + ffprobe (binary trong PATH) | Tach audio + sample frame mot luot |
| Scene Detection | PySceneDetect ContentDetector | Phat hien chuyen scene -> keyframe |
| Transcription | faster-whisper (mac dinh `small`) | Speech-to-text tren full audio |
| LLM | Qwen qua 9router (OpenAI-compatible) | Tom tat, Q&A, flashcards, quiz |
| Embedding | sentence-transformers/all-MiniLM-L6-v2 | Vector hoa segment |
| Vector Store | FAISS qua LlamaIndex | Luu / truy xuat |

## Cai dat va khoi chay

### 1. Yeu cau he thong
- Python 3.9+
- Node.js 16+
- **ffmpeg + ffprobe** trong PATH (Phase 1 yeu cau bat buoc)
  - Windows: `winget install ffmpeg` hoac `choco install ffmpeg`
  - Kiem tra: `ffmpeg -version` va `ffprobe -version`
- 9router da duoc cai dat: `npm install -g 9router`

### 2. Cau hinh moi truong
Tao file `.env` tai thu muc goc:

```env
# 9router / Qwen
NINE_ROUTER_URL=http://localhost:20128/v1
NINE_ROUTER_API_KEY=your_9router_key_here
QWEN_MODEL_NAME=qw/qwen3-coder-plus

# Storage
DATA_DIR=./data
JOBS_DIR=./data/jobs
PORT=8000

# Pipeline (v0.6 - tuy chon)
WHISPER_MODEL_SIZE=small        # tiny / base / small / medium / large-v3
WHISPER_BEAM_SIZE=1             # 1 = nhanh ~2x; bump len 5 neu can chinh xac hon (Phase 3)
WHISPER_VAD_MIN_SILENCE_MS=300  # cat im lang chat hon (Phase 3)
WHISPER_VAD_THRESHOLD=0.45      # nguong VAD (mac dinh 0.5)
WHISPER_CPU_THREADS=0           # 0 = auto (= os.cpu_count())
WHISPER_NUM_WORKERS=2           # pipeline parallelism noi bo cua ctranslate2
WHISPER_LANGUAGE=               # "" = auto-detect; "vi"/"en" = bo qua detect
WHISPER_MIN_CONFIDENCE=-1.0     # drop segment co avg_logprob thap hon nguong (-1 = tat)
FRAME_SAMPLE_FPS=1.0            # ffmpeg frame sampling
SCENE_THRESHOLD=27.0            # PySceneDetect ContentDetector threshold
MIN_SCENE_LEN_SEC=1.5           # min scene length
MAX_UPLOAD_BYTES=524288000      # 500 MB upload cap
MAP_PHASE_CONCURRENCY=4         # so call LLM song song trong Map phase (Phase 2)

# Phase 4 — OCR + VLM cascade (mac dinh TAT)
OCR_ENABLED=false               # bat de chay PaddleOCR + Qwen-VL tren keyframes
OCR_LANG=en                     # vi / en / ch / japan / korean / fr / de ...
OCR_MIN_TEXT_LEN=50             # < ky tu nay -> goi VLM mo ta anh
KEYFRAME_CONCURRENCY=4          # so keyframe phan tich song song
VLM_ENABLED=true                # tat de chi dung OCR (khong goi VLM)
VLM_MODEL_NAME=qw/qwen-vl-plus  # ten model multimodal tren 9router

LOG_LEVEL=INFO

# CORS (toi uu cho dev mac dinh)
# CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Khoi chay nhanh
Chi can mot lenh de chay ca frontend va backend:

```powershell
.\start-all.bat
```

Lenh nay se tu dong mo va chay:
- 9router
- FastAPI backend
- Vite frontend

### 4. Khoi chay thu cong

**Terminal 1 - 9router**
```bash
9router
```

**Terminal 2 - Backend**
```bash
pip install -r requirements.txt
python -m uvicorn apps.api.main:app --reload --port 8000
```

**Terminal 3 - Frontend**
```bash
cd apps/web-ui
npm install
npm run dev
```

## Cau truc du an (v0.4)

```text
CDIO 3/
|-- apps/
|   |-- api/              # FastAPI backend (main.py)
|   `-- web-ui/           # React frontend
|-- core/
|   |-- services/         # Orchestrator, RAG, Generation, Transcription, JobManager
|   `-- domain/           # Pydantic models
|-- processing/
|   |-- media_demux.py    # ffmpeg + ffprobe wrapper (Phase 1)
|   `-- scene_detector.py # PySceneDetect (Phase 1)
|-- data/jobs/            # Per-job: video.mp4, audio.wav, frames/, keyframes/, index/
|-- docs/                 # architecture, technical_pipeline, project_overview, data_contracts
|-- 9ROUTER_SETUP.md      # Huong dan 9router
`-- start-all.bat         # Script chay toan bo he thong
```

## Xu ly su co

- **`ffmpeg/ffprobe khong co trong PATH`**: cai ffmpeg va dam bao chay duoc tu terminal.
- **`python-multipart` thieu**: chay `pip install -r requirements.txt`.
- **Loi ket noi 9router**: dam bao `9router` dang chay tai port `20128`.
- **Loi Whisper/CUDA**: mac dinh du an dung CPU; doi `WHISPER_MODEL_SIZE` neu can.
- **Upload tra 413**: file vuot `MAX_UPLOAD_BYTES`.
- **Job tra 400 "job_id khong hop le"**: `job_id` phai la UUID hop le (chong path traversal).

## Tai lieu bo sung

- [9router Setup Guide](9ROUTER_SETUP.md)
- [Docs Folder](docs/)
