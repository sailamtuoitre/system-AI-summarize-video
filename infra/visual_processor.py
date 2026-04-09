import cv2
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class VisualProcessingService:
    """
    Dịch vụ xử lý hình ảnh: trích xuất khung hình (keyframes) từ video.
    """

    def __init__(self, diff_threshold: float = 0.5):
        """
        Args:
            diff_threshold (float): Ngưỡng thay đổi giữa 2 khung hình để coi là keyframe (0.0 - 1.0).
        """
        self.diff_threshold = diff_threshold

    def extract_keyframes(self, video_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """
        Quét video và trích xuất các khung hình quan trọng (ví dụ: khi đổi slide).
        
        Returns:
            List[Dict[str, Any]]: Danh sách thông tin keyframes (path, timestamp).
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Không thể mở video: {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        keyframes = []
        last_frame = None
        frame_count = 0
        
        logger.info(f"Bắt đầu trích xuất keyframes từ {video_path}...")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Chỉ kiểm tra mỗi giây 1 lần để tăng tốc độ xử lý
            if frame_count % int(fps) == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if last_frame is not None:
                    # Tính toán sự khác biệt giữa khung hình hiện tại và trước đó
                    frame_delta = cv2.absdiff(last_frame, gray)
                    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                    
                    # Tính tỷ lệ phần trăm pixel thay đổi
                    change_ratio = thresh.mean() / 255
                    
                    if change_ratio > self.diff_threshold / 10: # Điều chỉnh ngưỡng linh hoạt
                        timestamp = frame_count / fps
                        minutes = int(timestamp // 60)
                        seconds = int(timestamp % 60)
                        time_str = f"{minutes:02d}_{seconds:02d}"
                        
                        file_name = f"keyframe_{time_str}.jpg"
                        file_path = os.path.join(output_dir, file_name)
                        cv2.imwrite(file_path, frame)
                        
                        keyframes.append({
                            "path": file_path,
                            "timestamp": timestamp,
                            "time_str": f"{minutes:02d}:{seconds:02d}"
                        })
                        logger.info(f"Đã phát hiện chuyển cảnh tại {time_str}")

                last_frame = gray
            
            frame_count += 1

        cap.release()
        logger.info(f"Hoàn tất trích xuất. Tổng cộng {len(keyframes)} keyframes.")
        return keyframes
