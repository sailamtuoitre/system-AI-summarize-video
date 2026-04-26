export type JobStatus =
  | 'pending'
  | 'extracting_audio'
  | 'transcribing'
  | 'indexing'
  | 'generating_summary'
  | 'completed'
  | 'failed';

export type FeatureStatus = 'not_started' | 'processing' | 'ready' | 'failed';

export interface Evidence {
  timestamp: string;
  quote: string;
  source_node_id: string;
}

export interface SummaryOutput {
  initial_summary: string;
}

export interface Flashcard {
  front: string;
  back: string;
  latex?: string | null;
  evidence: Evidence;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  answer: string;
  explanation?: string;
  evidence: Evidence;
}

export interface ChunkProgress {
  chunk_duration_seconds: number;
  total_chunks: number;
  processed_chunks: number;
}

export interface JobState {
  job_id: string;
  video_path: string;
  filename?: string | null;
  status: JobStatus;
  created_at: string;
  completed_at?: string | null;
  features: Record<string, FeatureStatus>;
  summary?: SummaryOutput | null;
  flashcards: Flashcard[];
  quiz: QuizQuestion[];
  chunk_progress: ChunkProgress;
  latency: Record<string, number>;
  error_message?: string | null;
}

export interface UploadResponse {
  job_id: string;
  status: JobStatus;
}

export interface SourceCitation {
  timestamp: string;
  has_ocr: boolean;
  has_caption: boolean;
  has_visual_evidence: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  // Phase 4 (v0.7): richer per-source flags so the UI can show
  // OCR / VLM badges. Optional for backwards-compat with older backends.
  source_details?: SourceCitation[];
}
