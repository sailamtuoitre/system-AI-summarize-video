import React, { useState, useEffect } from 'react';
import SourcePanel from './components/SourcePanel';
import ChatPanel from './components/ChatPanel';
import StudioPanel from './components/StudioPanel';
import './App.css';

const App: React.FC = () => {
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobState, setJobState] = useState<any>(null);
  const [allJobs, setAllJobs] = useState<any[]>([]);
  const [isSourceOpen, setIsSourceOpen] = useState(true);
  const [isStudioOpen, setIsStudioOpen] = useState(true);
  const [activeView, setActiveView] = useState<'chat' | 'flashcards' | 'quiz'>('chat');

  // Fetch all jobs
  const fetchAllJobs = async () => {
    try {
      const response = await fetch('http://localhost:8000/jobs');
      if (response.ok) {
        const data = await response.json();
        setAllJobs(data);
        
        // If no current job selected, pick the first one
        if (!currentJobId && data.length > 0) {
          setCurrentJobId(data[0].job_id);
        }
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  useEffect(() => {
    fetchAllJobs();
  }, []);

  // Poll for current job status
  useEffect(() => {
    if (!currentJobId) return;
    
    // Find current job in allJobs to avoid extra fetch if already completed
    const current = allJobs.find(j => j.job_id === currentJobId);
    if (current && (current.status === 'completed' || current.status === 'failed')) {
        setJobState(current);
        return;
    }

    const fetchJobStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/job/${currentJobId}`);
        if (response.ok) {
          const data = await response.json();
          setJobState(data);
          
          // Refresh list if status changed to completed
          if (data.status === 'completed') {
              fetchAllJobs();
          }

          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(interval);
          }
        }
      } catch (error) {
        console.error('Error fetching job status:', error);
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

      <div className={`grid-wrapper ${!isSourceOpen ? 'source-closed' : ''} ${!isStudioOpen ? 'studio-closed' : ''}`}>
        <SourcePanel 
          currentJobId={currentJobId} 
          setCurrentJobId={setCurrentJobId}
          jobState={jobState}
          allJobs={allJobs}
          refreshJobs={fetchAllJobs}
          isOpen={isSourceOpen}
          togglePanel={() => setIsSourceOpen(!isSourceOpen)}
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
