import React, { useState, useRef, useEffect } from 'react';
import FlashcardsView from './FlashcardsView';
import MiniTestView from './MiniTestView';
import type { ChatResponse, JobState, SourceCitation } from '../types/api';

interface ChatPanelProps {
  jobId: string | null;
  jobState: JobState | null;
  isSourceOpen: boolean;
  isStudioOpen: boolean;
  toggleSource: () => void;
  toggleStudio: () => void;
  activeView: 'chat' | 'flashcards' | 'quiz';
  setActiveView: (view: 'chat' | 'flashcards' | 'quiz') => void;
  apiBaseUrl: string;
}

interface Message {
  role: 'user' | 'ai';
  content: string;
  sources?: string[];
  sourceDetails?: SourceCitation[];
}

const ChatPanel: React.FC<ChatPanelProps> = ({ 
  jobId, jobState, isSourceOpen, isStudioOpen, toggleSource, toggleStudio, activeView, setActiveView, apiBaseUrl
}) => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: 'Tôi đã phân tích video bài giảng. Bạn có thể hỏi bất kỳ điều gì về nội dung bài học!' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeView]);

  useEffect(() => {
    setMessages([
      {
        role: 'ai',
        content: jobId
          ? 'Mình đã chuyển sang video hiện tại. Bạn có thể hỏi về nội dung của video này.'
          : 'Tôi đã phân tích video bài giảng. Bạn có thể hỏi bất kỳ điều gì về nội dung bài học!'
      }
    ]);
  }, [jobId]);

  const handleSend = async (customPrompt?: string) => {
    const textToSend = customPrompt || input;
    if (!textToSend.trim() || !jobId || isLoading) return;

    if (!customPrompt) setInput('');
    setMessages(prev => [...prev, { role: 'user', content: textToSend }]);
    setIsLoading(true);
    setActiveView('chat');

    try {
      const response = await fetch(`${apiBaseUrl}/job/${jobId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: textToSend })
      });
      if (response.ok) {
        const data: ChatResponse = await response.json();
        setMessages(prev => [...prev, {
          role: 'ai',
          content: data.answer,
          sources: data.sources,
          sourceDetails: data.source_details,
        }]);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Chat không thành công.' }));
        setMessages(prev => [...prev, {
          role: 'ai',
          content: typeof errorData.detail === 'string' ? errorData.detail : 'Chat không thành công.'
        }]);
      }
    } catch (error) {
      console.error('Chat failed:', error);
      setMessages(prev => [...prev, { role: 'ai', content: 'Xin lỗi, đã có lỗi xảy ra.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderContent = () => {
    switch (activeView) {
      case 'flashcards':
        return jobState?.features?.flashcards === 'ready' ? (
          <FlashcardsView cards={jobState.flashcards} />
        ) : (
          <div className="empty-state">Vui lòng tạo Flashcards trong Studio trước.</div>
        );
      case 'quiz':
        return jobState?.features?.mini_test === 'ready' ? (
          <MiniTestView 
            questions={jobState.quiz} 
            onExplain={(wrongQs) => handleSend(`Giải thích giúp tôi các câu hỏi trắc nghiệm này: ${wrongQs}`)}
          />
        ) : (
          <div className="empty-state">Vui lòng tạo Mini-test trong Studio trước.</div>
        );
      default:
        return (
          <div className="panel-body chat-messages" ref={scrollRef}>
            {messages.map((msg, i) => (
              <div key={i} className={`msg ${msg.role}`}>
                {msg.content}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="citation">
                    📎 Nguồn: {(msg.sourceDetails && msg.sourceDetails.length === msg.sources.length
                      ? msg.sourceDetails
                      : msg.sources.map((t) => ({ timestamp: t, has_ocr: false, has_caption: false, has_visual_evidence: false }))
                    ).map((src: any, idx) => (
                      <span key={idx} className="src-chip" title={[
                        src.has_ocr && 'OCR text from slide',
                        src.has_caption && 'AI caption from slide',
                      ].filter(Boolean).join(' · ') || 'Transcript only'}>
                        {src.timestamp}
                        {src.has_ocr && <span className="src-badge ocr" aria-label="OCR">📄</span>}
                        {src.has_caption && <span className="src-badge vlm" aria-label="VLM caption">🤖</span>}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && <div className="msg ai typing">Đang suy nghĩ...</div>}
          </div>
        );
    }
  };

  const viewTitles = { chat: 'Cuộc trò chuyện', flashcards: 'Thẻ ghi nhớ', quiz: 'Mini-test' };

  return (
    <div className="panel chat-panel">
      <div className="panel-header">
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {!isSourceOpen && (
            <button className="restore-btn" onClick={toggleSource}>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M9 18l6-6-6-6"/></svg>
              Nguồn
            </button>
          )}
          <span className="panel-title">{viewTitles[activeView]}</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div className="pill-tabs">
            <button className={`pill-tab ${activeView === 'chat' ? 'active' : ''}`} onClick={() => setActiveView('chat')}>💬 Chat</button>
            <button className={`pill-tab ${activeView === 'flashcards' ? 'active' : ''}`} onClick={() => setActiveView('flashcards')}>🃏 Flashcards</button>
            <button className={`pill-tab ${activeView === 'quiz' ? 'active' : ''}`} onClick={() => setActiveView('quiz')}>📝 Quiz</button>
          </div>
          {!isStudioOpen && (
            <button className="restore-btn" onClick={toggleStudio}>
              Studio
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
          )}
        </div>
      </div>

      <div className="main-content-area">
        {renderContent()}
      </div>

      {activeView === 'chat' && (
        <div className="chat-input-area">
          <input 
            className="chat-input" type="text" 
            placeholder={jobId ? "Hỏi về nội dung video..." : "Tải video để bắt đầu chat"}
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                if (!jobId) alert("Vui lòng tải video lên trước khi chat!");
                else handleSend();
              }
            }}
            disabled={isLoading}
          />
          <button className="send-btn" onClick={() => !jobId ? alert("Vui lòng tải video lên trước khi chat!") : handleSend()} disabled={isLoading}>
            Gửi
          </button>
        </div>
      )}

      <style>{`
        .main-content-area { flex: 1; overflow-y: auto; background: #fff; }
        .empty-state { padding: 40px; text-align: center; color: var(--color-text-secondary); }
        .pill-tabs { display: flex; background: var(--color-background-secondary); padding: 4px; border-radius: 20px; border: 0.5px solid var(--color-border-tertiary); }
        .pill-tab { padding: 4px 12px; border: none; background: none; font-size: 11px; font-weight: 600; cursor: pointer; border-radius: 16px; color: var(--color-text-secondary); transition: all 0.2s; }
        .pill-tab.active { background: #fff; color: var(--color-primary); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        
        .chat-messages { display: flex; flex-direction: column; gap: 10px; padding: 12px; }
        .msg { max-width: 85%; padding: 10px 13px; border-radius: var(--border-radius-lg); font-size: 13px; line-height: 1.5; }
        .msg.ai { background: var(--color-background-secondary); border: 0.5px solid var(--color-border-tertiary); align-self: flex-start; }
        .msg.user { background: var(--color-primary); color: #fff; align-self: flex-end; }
        .citation { margin-top: 6px; padding: 6px 8px; background: #EEEDFE; border-left: 2px solid var(--color-primary); border-radius: 0 8px 8px 0; font-size: 11px; color: #3C3489; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
        .src-chip { display: inline-flex; align-items: center; gap: 3px; padding: 2px 7px; background: #fff; border: 0.5px solid #C7C2F0; border-radius: 999px; font-weight: 600; font-size: 10.5px; color: #3C3489; }
        .src-badge { font-size: 10px; line-height: 1; }
        .src-badge.ocr { color: #0F6E56; }
        .src-badge.vlm { color: #B45309; }
        
        .chat-input-area { padding: 10px 12px; border-top: 0.5px solid var(--color-border-tertiary); display: flex; gap: 8px; background: #fff; }
        .chat-input { flex: 1; padding: 8px 12px; border: 0.5px solid var(--color-border-tertiary); border-radius: var(--border-radius-md); font-size: 13px; outline: none; }
        .send-btn { padding: 8px 20px; background: var(--color-primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .restore-btn { display: flex; align-items: center; gap: 4px; padding: 4px 8px; background: var(--color-primary-light); color: var(--color-primary); border: 0.5px solid #AFA9EC; border-radius: 6px; font-size: 10px; font-weight: 600; cursor: pointer; }
      `}</style>
    </div>
  );
};

export default ChatPanel;
