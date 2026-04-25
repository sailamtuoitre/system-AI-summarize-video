import React, { useState, useEffect } from 'react';
import SourcePanel from './components/SourcePanel';
import ChatPanel from './components/ChatPanel';
import StudioPanel from './components/StudioPanel';
import './App.css';
import type { JobState } from './types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const App: React.FC = () => {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobState, setJobState] = useState<JobState | null>(null);
  const [allJobs, setAllJobs] = useState<JobState[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [isSourceOpen, setIsSourceOpen] = useState(true);
  const [isStudioOpen, setIsStudioOpen] = useState(true);
  const [activeView, setActiveView] = useState<'chat' | 'flashcards' | 'quiz'>('chat');

  // Fetch all jobs
  const fetchAllJobs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/jobs`);
      if (response.ok) {
        const data: JobState[] = await response.json();
        setAllJobs(data);
        setConnectionError(null);
        
        // If no current job selected, pick the first one
        if (!currentJobId && data.length > 0) {
          setCurrentJobId(data[0].job_id);
        }
      } else {
        setConnectionError(`Frontend reached the server, but ${API_BASE_URL}/jobs returned ${response.status}.`);
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
      setConnectionError(`Cannot connect to backend at ${API_BASE_URL}. Make sure FastAPI is running on port 8000.`);
    }
  };

  useEffect(() => {
    fetchAllJobs();
  }, []);

  useEffect(() => {
    if (!currentJobId) {
      setJobState(null);
      setActiveView('chat');
    }
  }, [currentJobId]);

  // Poll for current job status
  useEffect(() => {
    if (!currentJobId) return;
    
    // Find current job in allJobs to avoid extra fetch if already completed
    const current = allJobs.find(j => j.job_id === currentJobId);
    if (current && (current.status === 'completed' || current.status === 'failed')) {
        setJobState(current);
        return;
    }

    let consecutiveFailures = 0;
    const MAX_FAILURES = 5; // Stop polling after 5 consecutive connection failures

    const fetchJobStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/job/${currentJobId}`);
        if (response.ok) {
          const data: JobState = await response.json();
          setJobState(data);
          setConnectionError(null);
          consecutiveFailures = 0;
          
          // Refresh list if status changed to completed
          if (data.status === 'completed') {
              fetchAllJobs();
          }

          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(interval);
          }
        } else {
          setConnectionError(`Backend returned ${response.status} while loading job ${currentJobId}.`);
        }
      } catch (error) {
        consecutiveFailures++;
        console.error(`Error fetching job status (attempt ${consecutiveFailures}):`, error);
        setConnectionError(`Cannot connect to backend at ${API_BASE_URL}. Make sure FastAPI is running on port 8000.`);
        if (consecutiveFailures >= MAX_FAILURES) {
          clearInterval(interval);
          console.warn('Polling stopped after too many consecutive failures.');
        }
      }
    };

    fetchJobStatus();
    const interval = setInterval(fetchJobStatus, 3000);
    return () => clearInterval(interval);
  }, [currentJobId, allJobs]);

  return (
    <div className="app-container">
      <div className="topbar">
        <div className="logo">
          <svg viewBox="0 0 16 16"><path d="M3 8 L8 3 L13 8 L8 13Z"></path></svg>
        </div>
        <span className="app-name">Lecture AI</span>
        <div className="topbar-right">
          {/* Nút chức năng đã được gỡ bỏ */}
        </div>
      </div>

      {connectionError && (
        <div style={{
          margin: '12px 16px 0',
          padding: '10px 12px',
          borderRadius: '10px',
          border: '1px solid #FCA5A5',
          background: '#FEF2F2',
          color: '#991B1B',
          fontSize: '13px'
        }}>
          {connectionError}
        </div>
      )}

      <div className={`grid-wrapper ${!isSourceOpen ? 'source-closed' : ''} ${!isStudioOpen ? 'studio-closed' : ''}`}>
        <SourcePanel 
          currentJobId={currentJobId} 
          setCurrentJobId={setCurrentJobId}
          jobState={jobState}
          allJobs={allJobs}
          refreshJobs={fetchAllJobs}
          isOpen={isSourceOpen}
          togglePanel={() => setIsSourceOpen(!isSourceOpen)}
          apiBaseUrl={API_BASE_URL}
        />
        <ChatPanel 
          jobId={currentJobId} 
          jobState={jobState}
          isSourceOpen={isSourceOpen}
          isStudioOpen={isStudioOpen}
          toggleSource={() => setIsSourceOpen(true)}
          toggleStudio={() => setIsStudioOpen(true)}
          activeView={activeView}
          setActiveView={setActiveView}
          apiBaseUrl={API_BASE_URL}
        />
        <StudioPanel 
          jobId={currentJobId} 
          jobState={jobState}
          isOpen={isStudioOpen}
          togglePanel={() => setIsStudioOpen(!isStudioOpen)}
          activeView={activeView}
          setActiveView={setActiveView}
        />
      </div>
    </div>
  );
};

export default App;
