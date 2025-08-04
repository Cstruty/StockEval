import React, { useState, useEffect } from 'react';
import './App.css';

const defaultWeights = {
  roce: 30,
  interestCov: 30,
  grossMargin: 10,
  netMargin: 10,
  ccr: 5,
  gpAssets: 5,
  peRatio: 5,
  dividendYield: 5,
};

const quotes = [
  '“Be fearful when others are greedy and greedy when others are fearful.” – Warren Buffett',
  '“The intelligent investor is a realist who sells to optimists and buys from pessimists.” – Benjamin Graham',
  '“Know what you own, and know why you own it.” – Peter Lynch',
  '“Don’t look for the needle in the haystack. Just buy the haystack!” – John C. Bogle',
  '“The big money is not in the buying or selling, but in the waiting.” – Charlie Munger',
];

function useInterval(callback, delay) {
  useEffect(() => {
    const id = setInterval(callback, delay);
    return () => clearInterval(id);
  }, [callback, delay]);
}

function ScoreDonut({ score }) {
  const radius = 14;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? '#28a745' : score >= 50 ? 'orange' : 'red';
  return (
    <div className="score-donut" data-score={score}>
      <svg viewBox="0 0 40 40">
        <circle className="bg" cx="15" cy="20" r={radius} />
        <circle
          className="progress"
          cx="15"
          cy="20"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ stroke: color }}
        />
        <text x="15" y="20" textAnchor="middle" dominantBaseline="middle" style={{ fill: color }}>
          {score}
        </text>
      </svg>
    </div>
  );
}

function QuoteRotator() {
  const [index, setIndex] = useState(0);
  const [fade, setFade] = useState(true);

  useInterval(() => {
    setFade(false);
    setTimeout(() => {
      setIndex((i) => (i + 1) % quotes.length);
      setFade(true);
    }, 1000);
  }, 10000);

  return (
    <div id="quote-container" style={{ opacity: fade ? 1 : 0, transition: 'opacity 1s' }}>
      {quotes[index]}
    </div>
  );
}

function Toast({ message, onClose }) {
  useEffect(() => {
    if (message) {
      const id = setTimeout(onClose, 10000);
      return () => clearTimeout(id);
    }
  }, [message, onClose]);

  if (!message) return null;
  return (
    <div id="toast" className="show">
      <span id="toast-message">{message}</span>
      <button id="toast-close" onClick={onClose}>
        ✖
      </button>
    </div>
  );
}

function WeightModal({ weights, setWeights, deleted, toggleMetric, onClose }) {
  const total = Object.keys(weights).reduce((sum, k) => sum + Number(weights[k] || 0), 0);
  const radius = 25;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (total / 100) * circumference;

  const handleChange = (key, value) => {
    setWeights({ ...weights, [key]: Number(value) });
  };

  return (
    <div id="weight-modal" className="modal-overlay" style={{ display: 'flex' }}>
      <div id="weight-modal-content" className="modal-content">
        <div id="weight-header-content">
          <button className="modal-close" onClick={onClose}>
            ✖
          </button>
          <h3>Adjust Scoring Weights</h3>
        </div>
        <div className="weight-inputs">
          {Object.keys(defaultWeights).map((key) => (
            <div key={key} className={`weight-item${deleted.has(key) ? ' deleted' : ''}`}> 
              <button className="weight-toggle" onClick={() => toggleMetric(key)}>
                {deleted.has(key) ? <span className="green-plus">+</span> : '❌'}
              </button>
              <label>
                <span className={`metric-name${deleted.has(key) ? ' deleted' : ''}`}>{key}</span>
                <input
                  type="number"
                  value={weights[key] || 0}
                  onChange={(e) => handleChange(key, e.target.value)}
                  disabled={deleted.has(key)}
                />
              </label>
            </div>
          ))}
        </div>
        <div id="weight-chart-container">
          <div id="weight-chart">
            <div className="weight-label">Weight</div>
            <svg viewBox="0 0 100 100">
              <circle className="bg" cx="50" cy="30" r={radius} />
              <circle
                className="progress green"
                cx="50"
                cy="30"
                r={radius}
                strokeDasharray={circumference}
                strokeDashoffset={offset}
              />
              <text id="weight-chart-text" x="50" y="30" textAnchor="middle" dominantBaseline="middle">
                {total}
              </text>
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Watchlist() {
  const [weights, setWeights] = useState(defaultWeights);
  const [deleted, setDeleted] = useState(new Set());
  const [showWeight, setShowWeight] = useState(false);
  const [toast, setToast] = useState('');

  const toggleMetric = (key) => {
    setDeleted((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
        setWeights((w) => ({ ...w, [key]: 0 }));
      }
      return next;
    });
  };

  const stocks = [
    {
      ticker: 'UPWK',
      company: 'Upwork Inc.',
      price: '$12.92',
      dividendYield: 'N/A',
      peRatio: '7.78',
      roce: 7,
      interestCov: 15,
      grossMargin: 78,
      netMargin: 20,
      ccr: 71,
      gpAssets: 49,
      score: 92,
    },
  ];

  return (
    <div className="App">
      <nav>
        <a href="/">Home</a>
        <a href="/OtherTools">Tools</a>
        <a href="/AboutMe">About</a>
      </nav>
      <div id="initial-view" className="centered-view expanded">
        <h1>Stock Watchlist</h1>
        <button id="mobile-score-btn" onClick={() => setShowWeight(true)} title="Adjust scoring weights">
          ⚙
        </button>
        <QuoteRotator />
      </div>
      <div id="results-view">
        <table id="watchlist-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Company</th>
              <th>Price</th>
              <th>P/E Ratio</th>
              <th>ROCE</th>
              <th>Interest Coverage</th>
              <th>Gross Margin</th>
              <th>Net Margin</th>
              <th>CCR</th>
              <th>GP/Assets</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s) => (
              <tr key={s.ticker}>
                <td>{s.ticker}</td>
                <td>{s.company}</td>
                <td>{s.price}</td>
                <td>{s.peRatio}</td>
                <td>{s.roce}%</td>
                <td>{s.interestCov}x</td>
                <td>{s.grossMargin}%</td>
                <td>{s.netMargin}%</td>
                <td>{s.ccr}%</td>
                <td>{s.gpAssets}%</td>
                <td>
                  <ScoreDonut score={s.score} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showWeight && (
        <WeightModal
          weights={weights}
          setWeights={setWeights}
          deleted={deleted}
          toggleMetric={toggleMetric}
          onClose={() => setShowWeight(false)}
        />
      )}
      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  );
}

