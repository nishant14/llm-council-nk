import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import UserGuide from './UserGuide';
import { api } from '../api';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  onShowUserGuide,
  onStartNewConversation,
}) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('standard'); // 'standard' or 'persona'
  const [step, setStep] = useState(1); // 1: prompt input, 2: persona editor
  const [personas, setPersonas] = useState([]);
  const [mappingOption, setMappingOption] = useState('round_robin'); // 'round_robin' or 'matrix'
  const [isSuggestingPersonas, setIsSuggestingPersonas] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  // Reset steps and custom options when conversation changes
  useEffect(() => {
    setStep(1);
    setPersonas([]);
    setErrorMessage('');
  }, [conversation?.id]);

  const handleSuggestPersonas = async () => {
    if (!input.trim() || isSuggestingPersonas) return;
    setIsSuggestingPersonas(true);
    setErrorMessage('');
    try {
      const result = await api.suggestPersonas(input);
      setPersonas(result.personas || []);
      setStep(2);
    } catch (err) {
      console.error(err);
      setErrorMessage('Failed to generate personas. Please try again.');
    } finally {
      setIsSuggestingPersonas(false);
    }
  };

  const handleUpdatePersona = (index, field, value) => {
    const updated = [...personas];
    updated[index] = {
      ...updated[index],
      [field]: value
    };
    setPersonas(updated);
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;

    if (mode === 'persona' && step === 1) {
      handleSuggestPersonas();
    } else {
      // Standard send or persona run from Step 2
      const options = mode === 'persona'
        ? { mode: 'persona', personas, mappingOption }
        : { mode: 'standard' };

      onSendMessage(input, options);
      setInput('');
      setStep(1);
      setPersonas([]);
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return <UserGuide onStartNew={onStartNewConversation} />;
  }

  const isFirstMessage = conversation.messages.length === 0;

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">
                    LLM Council {msg.metadata?.mode === 'persona' && (
                      <span className="mode-badge">
                        Persona Mode ({msg.metadata?.mapping_option === 'matrix' ? 'Matrix' : 'Round-Robin'})
                      </span>
                    )}
                  </div>

                  {msg.error && (
                    <div className="error-message" style={{ marginBottom: '16px' }}>
                      {msg.error}
                    </div>
                  )}

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                    </div>
                  )}
                  {msg.stage2 && (
                    <Stage2
                      rankings={msg.stage2}
                      labelToModel={msg.metadata?.label_to_model}
                      aggregateRankings={msg.metadata?.aggregate_rankings}
                    />
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {isFirstMessage && (
        <div className="input-area">
          {step === 1 && (
            <div className="mode-selector">
              <button
                type="button"
                className={`mode-btn ${mode === 'standard' ? 'active' : ''}`}
                onClick={() => setMode('standard')}
                disabled={isSuggestingPersonas}
              >
                Standard Council
              </button>
              <button
                type="button"
                className={`mode-btn ${mode === 'persona' ? 'active' : ''}`}
                onClick={() => setMode('persona')}
                disabled={isSuggestingPersonas}
              >
                Persona Council (Variation 2)
              </button>
            </div>
          )}

          {isSuggestingPersonas && (
            <div className="suggesting-personas-overlay">
              <div className="spinner"></div>
              <span>Analyzing query & suggesting expert personas...</span>
            </div>
          )}

          {errorMessage && <div className="error-message">{errorMessage}</div>}

          {step === 1 && !isSuggestingPersonas && (
            <form className="input-form" onSubmit={handleSubmit}>
              <textarea
                className="message-input"
                placeholder={
                  mode === 'standard'
                    ? 'Ask your question... (Shift+Enter for new line, Enter to send)'
                    : 'Describe your problem. We will suggest 3 expert personas to explore it...'
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                rows={3}
              />
              <button
                type="submit"
                className="send-button"
                disabled={!input.trim() || isLoading}
              >
                {mode === 'standard' ? 'Send' : 'Suggest Personas'}
              </button>
            </form>
          )}

          {step === 2 && !isSuggestingPersonas && (
            <div className="persona-editor-container">
              <div className="editor-header">
                <h3>Configure Council Personas</h3>
                <p>Edit the generated personas and their constraints below before running the council.</p>
              </div>

              <div className="persona-cards-grid">
                {personas.map((persona, index) => (
                  <div key={index} className="persona-card">
                    <div className="card-field">
                      <label>Persona {index + 1} Name</label>
                      <input
                        type="text"
                        value={persona.name}
                        onChange={(e) => handleUpdatePersona(index, 'name', e.target.value)}
                      />
                    </div>
                    <div className="card-field">
                      <label>Focus / Weightage Instructions</label>
                      <textarea
                        rows={4}
                        value={persona.weightage}
                        onChange={(e) => handleUpdatePersona(index, 'weightage', e.target.value)}
                      />
                    </div>
                    <div className="card-field">
                      <label>Facets & Considerations (Not exhaustive)</label>
                      <textarea
                        rows={4}
                        value={persona.facets}
                        onChange={(e) => handleUpdatePersona(index, 'facets', e.target.value)}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mapping-selection-container">
                <label className="mapping-label">Model Assignment Option:</label>
                <div className="mapping-options">
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="mappingOption"
                      value="round_robin"
                      checked={mappingOption === 'round_robin'}
                      onChange={() => setMappingOption('round_robin')}
                    />
                    <div className="radio-text">
                      <strong>Option C: Round-Robin Distribution</strong>
                      <span>Assign each persona to one model sequentially (4 queries total). Fast and efficient.</span>
                    </div>
                  </label>
                  <label className="radio-label">
                    <input
                      type="radio"
                      name="mappingOption"
                      value="matrix"
                      checked={mappingOption === 'matrix'}
                      onChange={() => setMappingOption('matrix')}
                    />
                    <div className="radio-text">
                      <strong>Option B: All-to-All Matrix</strong>
                      <span>Every model answers from every persona's perspective (12 queries total). Multiplies API cost/time, but gives complete comparative coverage.</span>
                    </div>
                  </label>
                </div>
              </div>

              <div className="editor-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setStep(1)}
                >
                  Back (Edit Query)
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleSuggestPersonas}
                >
                  Regenerate Personas
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => handleSubmit()}
                >
                  Run Council
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      <div className="chat-footer">
        <span>LLM Council Consensus Engine</span>
        <span className="footer-dot">•</span>
        <button className="footer-link-btn" onClick={onShowUserGuide}>
          📖 View User Guide
        </button>
      </div>
    </div>
  );
}
