from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
import uuid
from dotenv import load_dotenv
from core.services.job_manager import JobManager
from core.services.orchestrator import VideoOrchestrator
from core.services.transcription_service import TranscriptionService
from core.services.rag_service import RAGService
from core.services.generation_service import GenerationService
from processing.media_demux import MediaDemuxer
from processing.scene_detector import SceneDetector
from processing.ocr_paddle import PaddleOCRService
from processing.vlm_qwen import QwenVLService
from processing.keyframe_analyzer import KeyframeAnalyzer

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Video Assistant API (Qwen 3.6 Plus Optimized)")

# Request models
class ChatRequest(BaseModel):
    """Request body cho endpoint chat."""
    question: str

def _get_allowed_origins() -> list[str]:
    origins = os.getenv("CORS_ALLOWED_ORIGINS")
    if origins:
        return [origin.strip() for origin in origins.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

# Cấu hình CORS - Cho phép tất cả để dev thuận tiện
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo các services (Dependency Injection)
job_manager = JobManager()
media_demuxer = MediaDemuxer(
    audio_sample_rate=16000,
    frame_fps=float(os.getenv("FRAME_SAMPLE_FPS", "1.0")),
)
scene_detector = SceneDetector(
    threshold=float(os.getenv("SCENE_THRESHOLD", "27.0")),
    min_scene_len=float(os.getenv("MIN_SCENE_LEN_SEC", "1.5")),
)
transcription_service = TranscriptionService(model_size=os.getenv("WHISPER_MODEL_SIZE", "small"))
rag_service = RAGService()
generation_service = GenerationService(
    api_key=os.getenv("NINE_ROUTER_API_KEY", os.getenv("DASHSCOPE_API_KEY")),
    model_name=os.getenv("QWEN_MODEL_NAME", "qwen-3.6-plus"),
    base_url=os.getenv("NINE_ROUTER_URL"),
)

# --- Phase 4: Keyframe analysis cascade (PaddleOCR -> Qwen-VL fallback) ---
# Disabled by default; flip OCR_ENABLED=true to turn it on.
_ocr_lang = os.getenv("OCR_LANG", "en")
paddle_ocr = PaddleOCRService(lang=_ocr_lang, use_gpu=False)
_vlm_enabled = os.getenv("VLM_ENABLED", "true").lower() in ("1", "true", "yes", "on")
qwen_vl = (
    QwenVLService(
        api_key=os.getenv("NINE_ROUTER_API_KEY", os.getenv("DASHSCOPE_API_KEY")),
        model_name=os.getenv("VLM_MODEL_NAME", "qw/qwen-vl-plus"),
        base_url=os.getenv("NINE_ROUTER_URL"),
    )
    if _vlm_enabled
    else None
)
keyframe_analyzer = KeyframeAnalyzer(ocr=paddle_ocr, vlm=qwen_vl)

orchestrator = VideoOrchestrator(
    job_manager,
    media_demuxer,
    scene_detector,
    transcription_service,
    rag_service,
    generation_service,
    keyframe_analyzer=keyframe_analyzer,
)

@app.get("/")
def root():
    return {
        "message": "AI Video Assistant API is running",
        "health": "/health",
        "docs": "/docs",
        "jobs": "/jobs",
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/jobs")
async def list_jobs():
    """Lấy danh sách tất cả các video đã tải lên."""
    return job_manager.list_all_jobs()

@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Tiếp nhận video và bắt đầu pipeline xử lý."""
    filename = file.filename or ""
    if not filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ định dạng .mp4")

    # Khởi tạo Job
    job_state = job_manager.create_job(filename)

    # Stream upload to disk with size cap to avoid filling the disk.
    total = 0
    try:
        with open(job_state.video_path, "wb") as buffer:
            while True:
                chunk = await file.read(UPLOAD_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    buffer.close()
                    try:
                        os.remove(job_state.video_path)
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"File vuot qua gioi han {MAX_UPLOAD_BYTES // (1024 * 1024)}MB",
                    )
                buffer.write(chunk)
    finally:
        await file.close()

    # Chạy pipeline xử lý ngầm
    background_tasks.add_task(orchestrator.run_initial_pipeline, job_state.job_id)

    return {"job_id": job_state.job_id, "status": job_state.status}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Lấy trạng thái và kết quả hiện tại của job."""
    _validate_job_id(job_id)
    job_state = job_manager.get_job_state(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    return job_state

@app.post("/job/{job_id}/feature/{feature_name}")
async def trigger_feature(job_id: str, feature_name: str, background_tasks: BackgroundTasks):
    """Kích hoạt các tính năng on-demand (flashcards, mini_test)."""
    _validate_job_id(job_id)
    if feature_name not in ["flashcards", "mini_test"]:
        raise HTTPException(status_code=400, detail="Tính năng không hợp lệ")

    background_tasks.add_task(orchestrator.generate_on_demand_feature, job_id, feature_name)
    return {"message": f"Đang bắt đầu xử lý {feature_name}"}

@app.post("/job/{job_id}/chat")
async def chat_with_video(job_id: str, request: ChatRequest):
    """Hỏi đáp dựa trên nội dung video."""
    _validate_job_id(job_id)
    job_state = job_manager.get_job_state(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")

    # Load index để retrieve
    index_path = os.path.join(os.path.dirname(job_state.video_path), "index")
    if not rag_service.load_index(index_path):
        raise HTTPException(status_code=409, detail="Index cua video chua san sang")

    # Retrieve & Answer
    nodes = rag_service.query(request.question, top_k=5)
    result = generation_service.answer_question(request.question, nodes)

    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
