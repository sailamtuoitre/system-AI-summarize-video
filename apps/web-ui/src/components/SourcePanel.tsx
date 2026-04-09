import React, { useState } from 'react';

interface SourcePanelProps {
  currentJobId: string | null;
  setCurrentJobId: (id: string) => void;
  jobState: any;
  allJobs: any[];
  refreshJobs: () => void;
  isOpen: boolean;
  togglePanel: () => void;
}

const SourcePanel: React.FC<SourcePanelProps> = ({ currentJobId, setCurrentJobId, jobState, allJobs, refreshJobs, isOpen, togglePanel }) => {
  const [isUploading, setIsUploading] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentJobId(data.job_id);
        refreshJobs();
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={`panel source-panel ${!isOpen ? 'closed' : ''}`} style={{ minWidth: isOpen ? '260px' : '0' }}>
      <div className="panel-header">
        <span className="panel-title">Nguồn</span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <svg 
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ cursor: 'pointer' }}
            onClick={togglePanel}
          >
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </div>
      </div>
      <div className="panel-body" style={{ opacity: isOpen ? 1 : 0, transition: 'opacity 0.2s' }}>
        <div className="upload-zone" onClick={() => !isUploading && document.getElementById('fileInput')?.click()}>
          <input 
            type="file" 
            id="fileInput" 
            hidden 
            accept=".mp4" 
            onChange={handleFileUpload}
            disabled={isUploading}
          />
          <div className="upload-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"></path>
            </svg>
          </div>
          <div className="upload-title">{isUploading ? 'Đang tải lên...' : 'Thêm video học thuật'}</div>
          <div className="upload-sub">MP4 · Tối đa 15 phút</div>
          <button 
            className="btn-upload" 
            disabled={isUploading}
            onClick={(e) => {
              e.stopPropagation(); // Ngăn sự kiện click bị lặp lại do div cha cũng có onClick
              document.getElementById('fileInput')?.click();
            }}
          >
            {isUploading ? 'Vui lòng đợi...' : '+ Tải lên'}
          </button>
        </div>

        <div style={{ padding: '6px 0 2px' }}>
          <div className="section-label">Đã lưu</div>
        </div>

        <div className="card-list-container">
          {allJobs.map((job, index) => {
            const colors = [
              { bg: '#F5F3FF', border: '#8B5CF6' }, // Purple
              { bg: '#EFF6FF', border: '#3B82F6' }, // Blue
              { bg: '#FFFBEB', border: '#F59E0B' }, // Yellow
              { bg: '#F0FDF4', border: '#10B981' }, // Green
            ];
            const color = colors[index % colors.length];
            const isActive = currentJobId === job.job_id;

            return (
              <div 
                key={job.job_id}
                className={`custom-card ${isActive ? 'active' : ''}`}
                style={{ 
                  backgroundColor: color.bg,
                  '--hover-border': color.border 
                } as any}
                onClick={() => setCurrentJobId(job.job_id)}
              >
                <div className="card-title">{job.filename || 'Video bài giảng'}</div>
                <div className="card-subtitle">
                  {job.status === 'completed' ? '✓ Đã xử lý hoàn tất' : '⏳ Đang trong hàng đợi...'}
                </div>
              </div>
            );
          })}
          
          {allJobs.length === 0 && !isUploading && (
            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-secondary)', fontSize: '11px' }}>
              Chưa có video nào được lưu.
            </div>
          )}
        </div>
      </div>

      <style>{`
        .card-list-container {
          height: 400px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding: 0 8px 0 0;
          scroll-behavior: smooth;
          scrollbar-width: none; /* Firefox */
          -ms-overflow-style: none;  /* IE and Edge */
        }
        
        .card-list-container::-webkit-scrollbar {
          display: none; /* Chrome, Safari, Opera */
        }

        .card-list-container:hover {
          scrollbar-width: thin;
        }

        .card-list-container:hover::-webkit-scrollbar {
          display: block;
          width: 3px;
        }

        .card-list-container::-webkit-scrollbar-thumb {
          background-color: #DDD6FE; /* Tím nhạt */
          border-radius: 10px;
        }

        .custom-card {
          padding: 12px 16px;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s ease;
          border-left: 3px solid transparent;
          flex-shrink: 0;
        }

        .custom-card:hover, .custom-card.active {
          border-left: 3px solid var(--hover-border);
          transform: translateX(2px);
        }

        .card-title {
          font-size: 13px;
          font-weight: 500;
          color: #1F2937;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin-bottom: 2px;
        }

        .card-subtitle {
          font-size: 11px;
          color: #6B7280;
          line-height: 1.4;
        }
        .upload-zone {
          border: 1.5px dashed var(--color-border-tertiary);
          border-radius: var(--border-radius-lg);
          padding: 24px 16px;
          text-align: center;
          cursor: pointer;
          background: var(--color-background-secondary);
          transition: all 0.2s;
        }
        .upload-zone:hover {
          border-color: var(--color-primary);
          background: var(--color-primary-light);
        }
        .upload-icon {
          width: 32px;
          height: 32px;
          margin: 0 auto 10px;
          background: #EEEDFE;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--color-primary);
        }
        .upload-icon svg { width: 16px; height: 16px; }
        .upload-title { font-size: 13px; font-weight: 500; margin-bottom: 4px; }
        .upload-sub { font-size: 11px; color: var(--color-text-secondary); }
        .btn-upload {
          margin-top: 12px;
          padding: 6px 14px;
          background: var(--color-primary);
          color: #fff;
          border: none;
          border-radius: var(--border-radius-md);
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
        }
        .source-item {
          padding: 10px 12px;
          border: 0.5px solid var(--color-border-tertiary);
          border-radius: var(--border-radius-md);
          background: var(--color-background-primary);
          cursor: pointer;
        }
        .source-item.active {
          border-color: #7F77DD;
          background: #EEEDFE;
        }
        .source-name { font-size: 12px; font-weight: 500; color: var(--color-text-primary); }
        .source-meta { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #1D9E75;
          display: inline-block;
          margin-right: 5px;
        }
        .status-badge {
          font-size: 10px;
          background: #E1F5EE;
          color: #0F6E56;
          padding: 2px 6px;
          border-radius: 4px;
        }
        .status-badge[data-status="pending"], .status-badge[data-status="processing"] {
          background: #FEF3C7;
          color: #92400E;
        }
        .progress-bar {
          height: 3px;
          background: var(--color-border-tertiary);
          border-radius: 2px;
          overflow: hidden;
          margin-top: 4px;
        }
        .progress-fill {
          height: 100%;
          background: var(--color-primary);
          transition: width 0.3s;
        }
      `}</style>
    </div>
  );
};

export default SourcePanel;
