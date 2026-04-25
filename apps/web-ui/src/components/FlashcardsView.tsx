import React, { useState, useEffect } from 'react';

interface Flashcard {
  front: string;
  back: string;
}

interface FlashcardsViewProps {
  cards: Flashcard[];
}

const FlashcardsView: React.FC<FlashcardsViewProps> = ({ cards }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [knownCount, setKnownCount] = useState(0);
  const [unknownCount, setUnknownCount] = useState(0);
  const [results, setResults] = useState<Array<'known' | 'unknown' | null>>(new Array(cards.length).fill(null));

  const currentCard = cards[currentIndex];

  const handleNext = (status: 'known' | 'unknown') => {
    const newResults = [...results];
    newResults[currentIndex] = status;
    setResults(newResults);

    if (status === 'known') setKnownCount(prev => prev + 1);
    else setUnknownCount(prev => prev + 1);

    if (currentIndex < cards.length - 1) {
      setCurrentIndex(prev => prev + 1);
      setIsFlipped(false);
    }
  };

  const reset = () => {
    setCurrentIndex(0);
    setIsFlipped(false);
    setKnownCount(0);
    setUnknownCount(0);
    setResults(new Array(cards.length).fill(null));
  };

  if (cards.length === 0) return <div>Chưa có flashcards.</div>;

  const isFinished = currentIndex === cards.length - 1 && results[currentIndex] !== null;

  return (
    <div className="flashcards-container">
      <div className="stats-row">
        <div className="stat-box">
          <div className="stat-val" style={{ color: '#1D9E75' }}>{knownCount}</div>
          <div className="stat-label">Đã thuộc</div>
        </div>
        <div className="stat-box">
          <div className="stat-val">{cards.length - knownCount - unknownCount}</div>
          <div className="stat-label">Còn lại</div>
        </div>
        <div className="stat-box">
          <div className="stat-val" style={{ color: '#DC2626' }}>{unknownCount}</div>
          <div className="stat-label">Chưa thuộc</div>
        </div>
      </div>

      <div className="progress-container">
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${((currentIndex + (results[currentIndex] ? 1 : 0)) / cards.length) * 100}%` }}></div>
        </div>
        <div className="progress-text">{currentIndex + (results[currentIndex] ? 1 : 0)} / {cards.length}</div>
      </div>

      {!isFinished ? (
        <div className="card-area">
          <div className={`flashcard ${isFlipped ? 'flipped' : ''}`} onClick={() => setIsFlipped(!isFlipped)}>
            <div className="card-side card-front">
              <div className="card-tag">Câu hỏi</div>
              <div className="card-text">{currentCard.front}</div>
              <div className="card-hint">Nhấn để xem đáp án</div>
            </div>
            <div className="card-side card-back">
              <div className="card-tag">Đáp án</div>
              <div className="card-text">{currentCard.back}</div>
            </div>
          </div>

          <div className="controls">
            {!isFlipped ? (
              <button className="btn-flip" onClick={() => setIsFlipped(true)}>Lật thẻ</button>
            ) : (
              <div className="action-btns">
                <button className="btn-unknown" onClick={() => handleNext('unknown')}>Chưa thuộc</button>
                <button className="btn-known" onClick={() => handleNext('known')}>Đã thuộc</button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="result-screen">
          <div className="result-icon">🎉</div>
          <h3>Hoàn thành bộ thẻ!</h3>
          <p>Bạn đã thuộc {knownCount}/{cards.length} khái niệm.</p>
          <button className="btn-flip" onClick={reset}>Làm lại từ đầu</button>
        </div>
      )}

      <style>{`
        .flashcards-container { padding: 20px; display: flex; flex-direction: column; gap: 20px; height: 100%; }
        .stats-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
        .stat-box { background: var(--color-background-secondary); padding: 12px; border-radius: var(--border-radius-md); text-align: center; border: 0.5px solid var(--color-border-tertiary); }
        .stat-val { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
        .stat-label { font-size: 11px; color: var(--color-text-secondary); }
        
        .progress-container { display: flex; align-items: center; gap: 12px; }
        .progress-bar { flex: 1; height: 4px; background: var(--color-border-tertiary); border-radius: 2px; overflow: hidden; }
        .progress-fill { height: 100%; background: var(--color-primary); transition: width 0.3s; }
        .progress-text { font-size: 11px; color: var(--color-text-secondary); min-width: 30px; }

        .card-area { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 30px; }
        .flashcard { width: 100%; max-width: 500px; height: 280px; position: relative; cursor: pointer; perspective: 1000px; }
        .card-side { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 30px; border: 1px solid var(--color-border-tertiary); border-radius: 16px; background: #fff; transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .card-back { transform: rotateY(180deg); background: var(--color-background-secondary); }
        .flashcard.flipped .card-front { transform: rotateY(180deg); }
        .flashcard.flipped .card-back { transform: rotateY(360deg); }
        
        .card-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 4px 8px; background: #EEEDFE; color: var(--color-primary); border-radius: 4px; position: absolute; top: 20px; }
        .card-text { font-size: 18px; font-weight: 500; text-align: center; line-height: 1.5; color: var(--color-text-primary); }
        .card-hint { font-size: 12px; color: var(--color-text-secondary); position: absolute; bottom: 20px; }

        .controls { display: flex; gap: 12px; }
        .btn-flip { padding: 10px 30px; background: var(--color-background-secondary); border: 1px solid var(--color-border-tertiary); border-radius: var(--border-radius-md); font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-flip:hover { background: #EEEDFE; border-color: var(--color-primary); color: var(--color-primary); }
        
        .action-btns { display: flex; gap: 12px; }
        .btn-known { padding: 10px 24px; background: #1D9E75; color: #fff; border: none; border-radius: var(--border-radius-md); font-weight: 600; cursor: pointer; }
        .btn-unknown { padding: 10px 24px; background: #DC2626; color: #fff; border: none; border-radius: var(--border-radius-md); font-weight: 600; cursor: pointer; }
        
        .result-screen { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 16px; justify-content: center; flex: 1; }
        .result-icon { font-size: 48px; }
      `}</style>
    </div>
  );
};

export default FlashcardsView;
