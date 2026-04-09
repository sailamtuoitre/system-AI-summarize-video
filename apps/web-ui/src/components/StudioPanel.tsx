import React, { useState } from 'react';

interface StudioPanelProps {
  jobId: string | null;
  jobState: any;
  isOpen: boolean;
  togglePanel: () => void;
  activeView: 'chat' | 'flashcards' | 'quiz';
  setActiveView: (view: 'chat' | 'flashcards' | 'quiz') => void;
}

const StudioPanel: React.FC<StudioPanelProps> = ({ 
  jobId, jobState, isOpen, togglePanel, activeView, setActiveView 
}) => {
  const triggerFeature = async (featureName: string, targetView: 'flashcards' | 'quiz') => {
    if (!jobId) {
        alert("Vui lòng tải video!");
        return;
    }
    
    // Switch view immediately if ready
    if (jobState?.features?.[featureName === 'mini_test' ? 'mini_test' : 'flashcards'] === 'ready') {
        setActiveView(targetView);
        return;
    }

    try {
      setActiveView(targetView); // Switch to show "please wait" state
      await fetch(`http://localhost:8000/job/${jobId}/feature/${featureName}`, {
        method: 'POST'
      });
    } catch (error) {
      console.error(`Failed to trigger ${featureName}:`, error);
    }
  };

  return (
    <div className={`panel studio-panel ${!isOpen ? 'closed' : ''}`} style={{ minWidth: isOpen ? '220px' : '0' }}>
      <div className="panel-header">
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <svg 
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            style={{ cursor: 'pointer' }}
            onClick={togglePanel}
          >
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </div>
        <span className="panel-title">Studio</span>
      </div>
      <div className="panel-body" style={{ opacity: isOpen ? 1 : 0, transition: 'opacity 0.2s' }}>
        <div>
          <div className="section-label">Tóm tắt tự động</div>
          <div className="summary-box">
            {jobState?.summary?.initial_summary || (jobId ? 'Đang tạo tóm tắt...' : 'Tải video để xem tóm tắt')}
          </div>
        </div>

        <div style={{ marginTop: '4px' }}>
          <div className="section-label">Công cụ on-demand</div>
          <div className="tool-grid">
            <button 
              className={`tool-btn ${activeView === 'flashcards' ? 'active' : ''}`} 
              onClick={() => triggerFeature('flashcards', 'flashcards')}
            >
              <div className="tool-btn-icon">🃏</div>
              <span className="tool-btn-label">Flashcards</span>
              <span className="tool-btn-sub">Thẻ ghi nhớ ↗</span>
            </button>
            <button 
              className={`tool-btn ${activeView === 'quiz' ? 'active' : ''}`} 
              onClick={() => triggerFeature('mini_test', 'quiz')}
            >
              <div className="tool-btn-icon">📝</div>
              <span className="tool-btn-label">Mini-test</span>
              <span className="tool-btn-sub">10 câu trắc nghiệm ↗</span>
            </button>
          </div>
        </div>

        {jobState?.features?.flashcards === 'ready' && jobState.flashcards?.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <div className="section-label">Flashcard mẫu</div>
            <div className="flashcard-preview" onClick={() => setActiveView('flashcards')} style={{ cursor: 'pointer' }}>
              <div className="fc-front">{jobState.flashcards[0].front}</div>
              <div className="fc-back">{jobState.flashcards[0].back}</div>
            </div>
          </div>
        )}

        {jobState?.features?.mini_test === 'ready' && jobState.quiz?.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <div className="section-label">Mini-test sẵn sàng</div>
            <div 
                className="summary-box" 
                style={{ background: '#E1F5EE', borderColor: '#0F6E56', color: '#0F6E56', cursor: 'pointer' }}
                onClick={() => setActiveView('quiz')}
            >
              ✓ Đã tạo {jobState.quiz.length} câu hỏi trắc nghiệm. Nhấn để làm bài.
            </div>
          </div>
        )}
      </div>

      <style>{`
        .summary-box { padding: 12px; background: var(--color-background-secondary); border-radius: var(--border-radius-md); font-size: 12px; line-height: 1.6; color: var(--color-text-primary); border: 0.5px solid var(--color-border-tertiary); min-height: 100px; }
        .tool-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
        .tool-btn { padding: 10px 8px; border: 0.5px solid var(--color-border-tertiary); border-radius: var(--border-radius-md); background: var(--color-background-secondary); cursor: pointer; text-align: center; transition: all 0.2s; font-family: var(--font-sans); }
        .tool-btn:hover { background: #EEEDFE; border-color: #AFA9EC; }
        .tool-btn.active { background: #EEEDFE; border-color: var(--color-primary); border-width: 1px; }
        .tool-btn-icon { font-size: 16px; margin-bottom: 4px; }
        .tool-btn-label { font-size: 11px; font-weight: 500; color: var(--color-text-primary); display: block; }
        .tool-btn-sub { font-size: 10px; color: var(--color-text-secondary); display: block; margin-top: 1px; }
        .flashcard-preview { border: 0.5px solid var(--color-border-tertiary); border-radius: var(--border-radius-md); overflow: hidden; }
        .fc-front { background: #EEEDFE; padding: 10px 12px; font-size: 12px; font-weight: 500; color: #3C3489; }
        .fc-back { background: var(--color-background-secondary); padding: 8px 12px; font-size: 11px; color: var(--color-text-secondary); }
      `}</style>
    </div>
  );
};

export default StudioPanel;
