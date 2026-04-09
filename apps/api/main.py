from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from dotenv import load_dotenv
from core.services.job_manager import JobManager
from core.services.orchestrator import VideoOrchestrator
from core.services.transcription_service import TranscriptionService
from core.services.rag_service import RAGService
from core.services.generation_service import GenerationService
from infra.audio_extractor import AudioExtractor
from infra.visual_processor import VisualProcessingService

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Video Assistant API (Qwen 3.6 Plus Optimized)")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo các services (Dependency Injection cho Qwen & Visual Processing)
job_manager = JobManager()
audio_extractor = AudioExtractor()
visual_processor = VisualProcessingService(diff_threshold=0.5) # Phát hiện đổi slide
transcription_service = TranscriptionService(model_size="small") # Whisper bản small cho tốc độ
rag_service = RAGService()
generation_service = GenerationService(
    api_key=os.getenv("DASHSCOPE_API_KEY"), 
    model_name="qwen-3.6-plus"
)

orchestrator = VideoOrchestrator(
    job_manager, 
    audio_extractor, 
    visual_processor, 
    transcription_service, 
    rag_service, 
    generation_service
)

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
    if not file.filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ định dạng .mp4")
    
    # Khởi tạo Job
    job_state = job_manager.create_job(file.filename)
    
    # Lưu file video thực tế
    with open(job_state.video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Chạy pipeline xử lý ngầm
    background_tasks.add_task(orchestrator.run_initial_pipeline, job_state.job_id)
    
    return {"job_id": job_state.job_id, "status": job_state.status}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Lấy trạng thái và kết quả hiện tại của job."""
    job_state = job_manager.get_job_state(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    return job_state

@app.post("/job/{job_id}/feature/{feature_name}")
async def trigger_feature(job_id: str, feature_name: str, background_tasks: BackgroundTasks):
    """Kích hoạt các tính năng on-demand (flashcards, mini_test)."""
    if feature_name not in ["flashcards", "mini_test"]:
        raise HTTPException(status_code=400, detail="Tính năng không hợp lệ")
    
    background_tasks.add_task(orchestrator.generate_on_demand_feature, job_id, feature_name)
    return {"message": f"Đang bắt đầu xử lý {feature_name}"}

@app.post("/job/{job_id}/chat")
async def chat_with_video(job_id: str, question: str):
    """Hỏi đáp dựa trên nội dung video."""
    job_state = job_manager.get_job_state(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    
    # Load index để retrieve
    index_path = os.path.join(os.path.dirname(job_state.video_path), "index")
    rag_service.load_index(index_path)
    
    # Retrieve & Answer
    nodes = rag_service.query(question, top_k=5)
    result = generation_service.answer_question(question, nodes)
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
