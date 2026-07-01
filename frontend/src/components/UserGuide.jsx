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
          <h2>⚙️ How the 3-Stage Process Works</h2>
          <div className="stages-flow">
            <div className="stage-card">
              <div className="stage-badge">Stage 1</div>
              <h3>Independent Answering</h3>
              <p>
                The council models (Gemini, Llama, DeepSeek, GPT) receive your query and answer it independently. They do not see other answers yet.
              </p>
            </div>
            <div className="stage-card">
              <div className="stage-badge">Stage 2</div>
              <h3>Peer Review & Ranking</h3>
              <p>
                All Stage 1 responses are anonymized. Each model acts as a reviewer, highlighting strengths and weaknesses of the other answers, and then ranks them.
              </p>
            </div>
            <div className="stage-card">
              <div className="stage-badge">Stage 3</div>
              <h3>Chairman Synthesis</h3>
              <p>
                A dedicated <strong>Chairman</strong> model (Gemini 2.5 Flash) reviews all initial answers, peer critiques, and average rankings to compile the final unified advice.
              </p>
            </div>
          </div>
        </div>

        <div className="user-guide-section">
          <h2>⚖️ Council Modes & Customization</h2>
          <div className="modes-grid">
            <div className="mode-card">
              <div className="mode-icon">🌐</div>
              <h3>Standard Mode</h3>
              <p>
                Standard consensus flow. Each model answers your query directly based on its general configuration. Ideal for direct exploration and fact-checking.
              </p>
            </div>
            <div className="mode-card">
              <div className="mode-icon">🎭</div>
              <h3>Persona Council Mode</h3>
              <p>
                Tailored exploration. Before the council runs, the system automatically suggests <strong>3 expert perspectives</strong> (personas) optimized to explore your query.
              </p>
            </div>
            <div className="mode-card">
              <div className="mode-icon">🔄</div>
              <h3>Option C: Round-Robin</h3>
              <p>
                You assign one model to each persona (one query per persona — the same model can be assigned to more than one persona). Fast and efficient.
              </p>
            </div>
            <div className="mode-card">
              <div className="mode-icon">🎛️</div>
              <h3>Option B: All-to-All Matrix</h3>
              <p>
                Every distinct model you've assigned answers from every persona's perspective. Provides full comparative coverage but multiplies API usage.
              </p>
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
