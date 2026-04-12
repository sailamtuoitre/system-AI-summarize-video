import logging
import os
from typing import List, Dict, Any, Optional
from llama_index.core import Document, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pathlib import Path

logger = logging.getLogger(__name__)

class RAGService:
    """
    Dịch vụ quản lý chỉ mục và truy xuất thông tin (RAG) sử dụng LlamaIndex.
    """

    def __init__(self, embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Khởi tạo RAGService.
        
        Args:
            embed_model_name (str): Tên mô hình embedding để vector hóa văn bản.
        """
        logger.info(f"Đang khởi tạo RAGService với embedding model: {embed_model_name}...")
        self.embed_model = HuggingFaceEmbedding(model_name=embed_model_name)
        self.node_parser = SentenceSplitter(chunk_size=200, chunk_overlap=20)
        self._index = None

    def _format_timestamp(self, seconds: float) -> str:
        """Chuyển đổi giây sang định dạng mm:ss."""
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def build_index_from_segments(self, segments: List[Dict[str, Any]], storage_path: str, 
                                   keyframes: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Xây dựng vector index từ các segments của transcript và keyframes.

        Args:
            segments (List[Dict[str, Any]]): Danh sách các phân đoạn văn bản từ Whisper.
            storage_path (str): Đường dẫn lưu trữ index cục bộ.
            keyframes (Optional[List[Dict[str, Any]]]): Danh sách keyframes để tích hợp visual evidence.

        Returns:
            bool: True nếu xây dựng thành công, False nếu có lỗi.
        """
        try:
            documents = []
            for seg in segments:
                # Tìm keyframes gần với segment này (trong vòng 30 giây)
                related_keyframes = []
                if keyframes:
                    for kf in keyframes:
                        time_diff = abs(kf["timestamp"] - seg["start"])
                        if time_diff <= 30:  # Keyframe trong vòng 30 giây
                            related_keyframes.append(kf)

                # Mỗi segment coi như một document nhỏ với đầy đủ metadata
                doc = Document(
                    text=seg["text"],
                    metadata={
                        "start_time": seg["start"],
                        "end_time": seg["end"],
                        "timestamp_mmss": self._format_timestamp(seg["start"]),
                        "segment_id": seg["id"],
                        "has_visual_evidence": len(related_keyframes) > 0,
                        "keyframes": related_keyframes  # Lưu thông tin keyframes
                    }
                )
                documents.append(doc)

            logger.info(f"Bắt đầu xây dựng Index từ {len(documents)} phân đoạn (với {len(keyframes or [])} keyframes)...")

            # Tạo index từ các documents
            self._index = VectorStoreIndex.from_documents(
                documents,
                embed_model=self.embed_model,
                transformations=[self.node_parser]
            )

            # Lưu index xuống ổ đĩa
            Path(storage_path).mkdir(parents=True, exist_ok=True)
            self._index.storage_context.persist(persist_dir=storage_path)

            logger.info(f"Đã xây dựng và lưu Index thành công tại: {storage_path}")
            return True

        except Exception as e:
            logger.error(f"Lỗi khi xây dựng Index: {str(e)}")
            return False

    def load_index(self, storage_path: str) -> bool:
        """
        Tải index đã lưu từ ổ đĩa.
        
        Args:
            storage_path (str): Đường dẫn lưu trữ index.
            
        Returns:
            bool: True nếu tải thành công, False nếu có lỗi.
        """
        try:
            if not os.path.exists(storage_path):
                logger.error(f"Không tìm thấy thư mục Index tại: {storage_path}")
                return False
                
            storage_context = StorageContext.from_defaults(persist_dir=storage_path)
            self._index = load_index_from_storage(
                storage_context, 
                embed_model=self.embed_model
            )
            logger.info(f"Đã tải thành công Index từ: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải Index: {str(e)}")
            return False

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Truy vấn thông tin liên quan từ Index.
        
        Args:
            query_text (str): Câu hỏi hoặc nội dung cần tìm kiếm.
            top_k (int): Số lượng kết quả liên quan nhất cần trả về.
            
        Returns:
            List[Dict[str, Any]]: Danh sách các kết quả kèm metadata.
        """
        if self._index is None:
            logger.error("Chưa tải hoặc xây dựng Index.")
            return []

        retriever = self._index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query_text)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.node.get_content(),
                "score": node.score,
                "metadata": node.node.metadata,
                "node_id": node.node.node_id
            })
            
        return results
