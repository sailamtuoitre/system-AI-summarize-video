import React, { useState, useEffect } from 'react';

interface QuizQuestion {
  question: string;
  options: string[];
  answer: string;
  explanation?: string;
}

interface MiniTestViewProps {
  questions: QuizQuestion[];
  onExplain?: (question: string) => void;
}

const MiniTestView: React.FC<MiniTestViewProps> = ({ questions, onExplain }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(120); // 2 minutes
  const [isFinished, setIsFinished] = useState(false);
  const [wrongQuestions, setWrongQuestions] = useState<QuizQuestion[]>([]);

  // Function để reset quiz thay vì reload toàn bộ trang
  const resetQuiz = () => {
    setCurrentIndex(0);
    setSelectedOption(null);
    setIsAnswered(false);
    setScore(0);
    setTimeLeft(120);
    setIsFinished(false);
    setWrongQuestions([]);
  };

  useEffect(() => {
    if (timeLeft > 0 && !isFinished) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    } else if (timeLeft === 0) {
      setIsFinished(true);
    }
  }, [timeLeft, isFinished]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleOptionSelect = (option: string) => {
    if (isAnswered) return;
    setSelectedOption(option);
  };

  const handleSubmit = () => {
    if (!selectedOption) return;
    setIsAnswered(true);
    if (selectedOption === questions[currentIndex].answer) {
      setScore(score + 1);
    } else {
      setWrongQuestions([...wrongQuestions, questions[currentIndex]]);
    }
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setSelectedOption(null);
      setIsAnswered(false);
    } else {
      setIsFinished(true);
    }
  };

  if (questions.length === 0) return <div>Chưa có câu hỏi trắc nghiệm.</div>;

  const currentQ = questions[currentIndex];

  return (
    <div className="minitest-container">
      {!isFinished ? (
        <>
          <div className="test-header">
            <div className="q-progress">Câu {currentIndex + 1} / {questions.length}</div>
            <div className="timer">{formatTime(timeLeft)}</div>
          </div>
          
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}></div>
          </div>

          <div className="question-area">
            <h3 className="question-text">{currentQ.question}</h3>
            
            <div className="options-grid">
              {currentQ.options.map((opt, i) => {
                const char = String.fromCharCode(65 + i);
                let className = 'option-btn';
                if (selectedOption === opt) className += ' selected';
                if (isAnswered) {
                  if (opt === currentQ.answer) className += ' correct';
                  else if (selectedOption === opt) className += ' wrong';
                }

                return (
                  <button 
                    key={i} 
                    className={className}
                    onClick={() => handleOptionSelect(opt)}
                    disabled={isAnswered}
                  >
                    <span className="opt-char">{char}</span>
                    <span className="opt-text">{opt}</span>
                  </button>
                );
              })}
            </div>

            {isAnswered && (
              <div className={`feedback ${selectedOption === currentQ.answer ? 'correct' : 'wrong'}`}>
                <div className="feedback-title">
                  {selectedOption === currentQ.answer ? '✓ Chính xác!' : '✕ Sai rồi!'}
                </div>
                <div className="explanation">
                  <strong>Giải thích:</strong> {currentQ.explanation || 'Đáp án đúng là ' + currentQ.answer}
                </div>
              </div>
            )}
          </div>

          <div className="test-footer">
            {!isAnswered ? (
              <button className="submit-btn" onClick={handleSubmit} disabled={!selectedOption}>
                Gửi đáp án
              </button>
            ) : (
              <button className="submit-btn" onClick={handleNext}>
                {currentIndex < questions.length - 1 ? 'Tiếp theo →' : 'Xem kết quả'}
              </button>
            )}
          </div>
        </>
      ) : (
        <div className="result-screen">
          <div className="score-circle">
            <div className="score-num">{Math.round((score / questions.length) * 10)}</div>
            <div className="score-label">Điểm</div>
          </div>
          <h3>Kết quả bài làm</h3>
          <p>Bạn đã trả lời đúng {score}/{questions.length} câu hỏi.</p>
          
          <div className="stats-row">
            <div className="res-stat"><strong>{score}</strong> Đúng</div>
            <div className="res-stat"><strong>{questions.length - score}</strong> Sai</div>
          </div>

          {wrongQuestions.length > 0 && (
            <button className="explain-btn" onClick={() => onExplain?.(JSON.stringify(wrongQuestions))}>
              🔍 Xem giải thích chi tiết các câu sai
            </button>
          )}

          <button className="restart-btn" onClick={resetQuiz}>Làm bài mới</button>
        </div>
      )}

      <style>{`
        .minitest-container { padding: 20px; display: flex; flex-direction: column; gap: 16px; height: 100%; }
        .test-header { display: flex; justify-content: space-between; align-items: center; }
        .q-progress { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); }
        .timer { padding: 4px 12px; background: #EEEDFE; color: var(--color-primary); border-radius: 20px; font-weight: 700; font-family: monospace; }
        
        .progress-bar { height: 4px; background: var(--color-border-tertiary); border-radius: 2px; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--color-primary); transition: width 0.3s; }

        .question-area { flex: 1; display: flex; flex-direction: column; gap: 20px; padding-top: 10px; }
        .question-text { font-size: 18px; font-weight: 600; line-height: 1.4; }
        
        .options-grid { display: flex; flex-direction: column; gap: 10px; }
        .option-btn { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border: 1.5px solid var(--color-border-tertiary); border-radius: 12px; background: #fff; cursor: pointer; text-align: left; transition: all 0.2s; }
        .option-btn:hover:not(:disabled) { border-color: var(--color-primary); background: var(--color-primary-light); }
        .option-btn.selected { border-color: var(--color-primary); background: var(--color-primary-light); }
        .option-btn.correct { border-color: #1D9E75; background: #E1F5EE; }
        .option-btn.wrong { border-color: #DC2626; background: #FEE2E2; }
        
        .opt-char { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--color-border-tertiary); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: var(--color-text-secondary); background: #f9fafb; flex-shrink: 0; }
        .option-btn.selected .opt-char { border-color: var(--color-primary); color: var(--color-primary); background: #fff; }
        .opt-text { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }

        .feedback { padding: 16px; border-radius: 12px; margin-top: 10px; }
        .feedback.correct { background: #E1F5EE; border: 1px solid #1D9E75; color: #0F6E56; }
        .feedback.wrong { background: #FEE2E2; border: 1px solid #DC2626; color: #991B1B; }
        .feedback-title { font-weight: 700; margin-bottom: 4px; }
        .explanation { font-size: 13px; line-height: 1.5; }

        .test-footer { display: flex; justify-content: flex-end; padding-top: 20px; }
        .submit-btn { padding: 10px 24px; background: var(--color-primary); color: #fff; border: none; border-radius: var(--border-radius-md); font-weight: 600; cursor: pointer; transition: transform 0.1s; }
        .submit-btn:active { transform: scale(0.98); }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .result-screen { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 20px; text-align: center; }
        .score-circle { width: 100px; height: 100px; border-radius: 50%; border: 8px solid var(--color-primary); display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .score-num { font-size: 32px; font-weight: 800; color: var(--color-primary); line-height: 1; }
        .score-label { font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--color-text-secondary); }
        
        .stats-row { display: flex; gap: 20px; }
        .res-stat { font-size: 14px; }
        .res-stat strong { font-size: 18px; }
        
        .explain-btn { padding: 10px 20px; background: #EEEDFE; color: var(--color-primary); border: 1px solid #AFA9EC; border-radius: var(--border-radius-md); font-weight: 600; cursor: pointer; }
        .restart-btn { font-size: 13px; color: var(--color-text-secondary); background: none; border: none; cursor: pointer; text-decoration: underline; }
      `}</style>
    </div>
  );
};

export default MiniTestView;
