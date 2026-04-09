import os
import logging
from moviepy.editor import VideoFileClip
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioExtractor:
    """
    Tiện ích trích xuất âm thanh từ file video.
    """

    @staticmethod
    def extract_audio(video_path: str, audio_output_path: str, sample_rate: int = 16000) -> bool:
        """
        Trích xuất âm thanh từ video và lưu dưới định dạng WAV.
        
        Args:
            video_path (str): Đường dẫn tới file video gốc.
            audio_output_path (str): Đường dẫn lưu file âm thanh trích xuất.
            sample_rate (int): Tốc độ lấy mẫu (mặc định 16000Hz cho Whisper).
            
        Returns:
            bool: True nếu trích xuất thành công, False nếu có lỗi.
        """
        try:
            video_path_obj = Path(video_path)
            if not video_path_obj.exists():
                logger.error(f"Không tìm thấy file video tại: {video_path}")
                return False

            # Đảm bảo thư mục đầu ra tồn tại
            Path(audio_output_path).parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Bắt đầu trích xuất âm thanh từ {video_path}...")
            
            # Sử dụng moviepy để tách audio
            with VideoFileClip(video_path) as video:
                if video.audio is None:
                    logger.error("Video không có luồng âm thanh.")
                    return False
                
                # Ghi file audio với cấu hình tối ưu cho Whisper
                video.audio.write_audiofile(
                    audio_output_path,
                    fps=sample_rate,
                    nbytes=2,
                    codec='pcm_s16le', # Định dạng WAV chuẩn
                    ffmpeg_params=["-ac", "1"], # Mono
                    logger=None # Tắt log của moviepy để sạch console
                )
            
            logger.info(f"Trích xuất âm thanh thành công: {audio_output_path}")
            return True

        except Exception as e:
            logger.error(f"Lỗi khi trích xuất âm thanh: {str(e)}")
            return False
        finally:
            # Moviepy đôi khi giữ file handle, đảm bảo dọn dẹp nếu cần
            pass
