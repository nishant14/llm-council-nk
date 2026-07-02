import React from 'react';
import './UserGuide.css';

export default function UserGuide({ onStartNew }) {
  return (
    <div className="user-guide-wrapper">
      <div className="user-guide-container">
        <div className="user-guide-header">
          <div className="guide-logo-container">
            <span className="logo-emoji">🏛️</span>
          </div>
          <h1>Welcome to LLM Council</h1>
          <p className="subtitle">
            Harness the collective wisdom of a panel of AI models coordinated by a Chairman.
          </p>
        </div>

        <div className="guide-card welcome-card">
          <h2>💡 What is LLM Council?</h2>
          <p>
            Instead of consulting a single AI model (which can have biases, hallucination tendencies, or blind spots), the <strong>LLM Council</strong> framework runs your question through a three-stage consensus process. It polls a diverse group of models, has them review each other's work, and then synthesizes the best ideas into a unified response.
          </p>
        </div>

        <div className="user-guide-section">
          <h2>How it works</h2>
          <div className="process-flow">
            <div className="flow-node">
              <div className="flow-icon">🤖🤖🤖</div>
              <div className="flow-badge">Stage 1</div>
              <div className="flow-caption">Models answer on their own</div>
              <div className="flow-hint">🎛️ You pick the models</div>
            </div>
            <div className="flow-arrow" aria-hidden="true">→</div>
            <div className="flow-node">
              <div className="flow-icon">🕵️</div>
              <div className="flow-badge">Stage 2</div>
              <div className="flow-caption">Anonymous peer review &amp; ranking</div>
            </div>
            <div className="flow-arrow" aria-hidden="true">→</div>
            <div className="flow-node">
              <div className="flow-icon">🏛️</div>
              <div className="flow-badge">Stage 3</div>
              <div className="flow-caption">Chairman combines the best</div>
              <div className="flow-hint">🎛️ You pick the Chairman</div>
            </div>
            <div className="flow-arrow" aria-hidden="true">→</div>
            <div className="flow-node flow-node-final">
              <div className="flow-icon">⭐</div>
              <div className="flow-caption">Your answer</div>
            </div>
          </div>
        </div>

        <div className="user-guide-section">
          <h2>Two ways to run it</h2>
          <div className="mode-choice">
            <div className="mode-branch">
              <div className="mode-icon">🌐</div>
              <div className="mode-name">Standard</div>
              <div className="flow-caption">Every model answers directly</div>
              <div className="mode-hint">🎛️ You still pick the Chairman</div>
            </div>
            <div className="mode-branch">
              <div className="mode-icon">🎭</div>
              <div className="mode-name">Persona</div>
              <div className="flow-caption">3 expert viewpoints explore your question</div>
              <div className="mode-hint">✏️ Edit the personas, their weights &amp; each model</div>
              <div className="mapping-mini">
                <div className="mini-option">
                  <div className="mini-icon">🔄</div>
                  <div className="mini-name">Round-Robin</div>
                  <div className="flow-caption">One model per persona</div>
                </div>
                <div className="mini-option">
                  <div className="mini-icon">🎛️</div>
                  <div className="mini-name">Matrix</div>
                  <div className="flow-caption">Every model × every persona</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="user-guide-cta">
          <button className="start-btn" onClick={onStartNew}>
            + Start a Conversation
          </button>
        </div>
      </div>
    </div>
  );
}
