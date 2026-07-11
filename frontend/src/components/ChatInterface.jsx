import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import UserGuide from './UserGuide';
import CopyButton from './CopyButton';
import { buildFullAnswerHtml } from '../utils/exportRichText';
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
  const [availableModels, setAvailableModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState(''); // '' = backend default
  // attachment: null | {file_name, extracted_text, truncated, loading, error}
  const [attachment, setAttachment] = useState(null);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  // Load the list of council models available for the persona model dropdown
  useEffect(() => {
    api.getAvailableModels()
      .then((result) => setAvailableModels(result.council_models || []))
      .catch((err) => console.error('Failed to load available models:', err));
  }, []);

  // Reset steps and custom options when conversation changes
  useEffect(() => {
    setStep(1);
    setPersonas([]);
    setErrorMessage('');
    setAttachment(null);
  }, [conversation?.id]);

  const withDefaults = (personaList) => {
    const n = personaList.length;
    return personaList.map((persona, index) => {
      const defaultWeight = index === n - 1
        ? +(1 - (Math.round((1 / n) * 100) / 100) * (n - 1)).toFixed(2)
        : Math.round((1 / n) * 100) / 100;
      return {
        ...persona,
        model: persona.model || (availableModels.length
          ? availableModels[index % availableModels.length].id
          : ''),
        weight: persona.weight !== undefined ? persona.weight : defaultWeight,
      };
    });
  };

  const TIER_LABELS = { low: 'Low cost', medium: 'Medium cost', max: 'Max cost' };
  const modelsByTier = ['low', 'medium', 'max']
    .map((tier) => ({ tier, models: availableModels.filter((m) => m.tier === tier) }))
    .filter((g) => g.models.length > 0);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = ''; // allow re-selecting the same file
    setAttachment({ file_name: file.name, loading: true, error: null });
    try {
      const result = await api.extractFile(file);
      setAttachment({
        file_name: result.file_name,
        extracted_text: result.extracted_text,
        truncated: result.truncated,
        loading: false,
        error: null,
      });
    } catch (err) {
      setAttachment({ file_name: file.name, loading: false, error: err.message });
    }
  };

  const handleSuggestPersonas = async () => {
    if (!input.trim() || isSuggestingPersonas) return;
    setIsSuggestingPersonas(true);
    setErrorMessage('');
    try {
      // Include file content in persona suggestion so personas are relevant to the attachment
      const queryForPersonas = attachment?.extracted_text
        ? `${input}\n\n[Attached file: ${attachment.file_name}]\n${attachment.extracted_text}`
        : input;
      const result = await api.suggestPersonas(queryForPersonas);
      setPersonas(withDefaults(result.personas || []));
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
      if (mode === 'persona' && !isWeightValid) return;

      // Standard send or persona run from Step 2
      const options = mode === 'persona'
        ? { mode: 'persona', personas, mappingOption, chairmanModel, attachment }
        : { mode: 'standard', chairmanModel, attachment };

      onSendMessage(input, options);
      setInput('');
      setStep(1);
      setPersonas([]);
      setAttachment(null);
    }
  };

  const totalWeight = personas.reduce((sum, p) => sum + (parseFloat(p.weight) || 0), 0);
  const isWeightValid = Math.abs(totalWeight - 1) <= 0.01;

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
                    {msg.attachment?.file_name && (
                      <div className="attachment-badge">📎 {msg.attachment.file_name}</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">
                    <span>
                      LLM Council {msg.metadata?.mode === 'persona' && (
                        <span className="mode-badge">
                          Persona Mode ({msg.metadata?.mapping_option === 'matrix' ? 'Matrix' : 'Round-Robin'})
                        </span>
                      )}
                    </span>
                    {(msg.stage1 || msg.stage2 || msg.stage3) && (
                      <CopyButton getHtml={() => buildFullAnswerHtml(msg)} label="Export answer" />
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

          {step === 1 && (
            <div className="chairman-selector">
              <label htmlFor="chairman-model">Chairman model (final synthesis):</label>
              <select
                id="chairman-model"
                value={chairmanModel}
                onChange={(e) => setChairmanModel(e.target.value)}
                disabled={isSuggestingPersonas}
              >
                <option value="">Default (Gemini 2.5 Flash)</option>
                {modelsByTier.map(({ tier, models }) => (
                  <optgroup key={tier} label={TIER_LABELS[tier]}>
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>{m.id}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
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

              {/* File attachment strip */}
              <div className="attachment-strip">
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".txt,.docx,.pdf,.png,.jpg,.jpeg,.gif,.webp"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                {!attachment && (
                  <button
                    type="button"
                    className="attach-button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isLoading}
                  >
                    📎 Attach file
                  </button>
                )}
                {attachment?.loading && (
                  <div className="attachment-pill loading">
                    <div className="spinner spinner-sm" /> Extracting…
                  </div>
                )}
                {attachment && !attachment.loading && !attachment.error && (
                  <div className="attachment-pill">
                    📎 {attachment.file_name}
                    {attachment.truncated && <span className="truncated-warning"> ⚠️ truncated</span>}
                    <button type="button" className="attachment-remove" onClick={() => setAttachment(null)}>×</button>
                  </div>
                )}
                {attachment?.error && (
                  <div className="attachment-pill error">
                    ⚠️ {attachment.error}
                    <button type="button" className="attachment-remove" onClick={() => setAttachment(null)}>×</button>
                  </div>
                )}
              </div>

              <button
                type="submit"
                className="send-button"
                disabled={!input.trim() || isLoading || attachment?.loading}
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

              {/* Show attached file in step 2 so the user knows it will be included */}
              {attachment && !attachment.loading && !attachment.error && (
                <div className="attachment-strip">
                  <div className="attachment-pill">
                    📎 {attachment.file_name}
                    {attachment.truncated && <span className="truncated-warning"> ⚠️ truncated</span>}
                    <button type="button" className="attachment-remove" onClick={() => setAttachment(null)}>×</button>
                  </div>
                </div>
              )}

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
                      <label>Model</label>
                      <select
                        value={persona.model || ''}
                        onChange={(e) => handleUpdatePersona(index, 'model', e.target.value)}
                      >
                        {modelsByTier.map(({ tier, models }) => (
                          <optgroup key={tier} label={TIER_LABELS[tier]}>
                            {models.map((m) => (
                              <option key={m.id} value={m.id}>{m.id}</option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </div>
                    <div className="card-field">
                      <label>Weight (0-1, all personas should sum to 1)</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="1"
                        value={persona.weight}
                        onChange={(e) => handleUpdatePersona(index, 'weight', e.target.value === '' ? '' : parseFloat(e.target.value))}
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

              <div className={`weight-total ${isWeightValid ? 'valid' : 'invalid'}`}>
                Total weight: {totalWeight.toFixed(2)} {!isWeightValid && '(must sum to 1.00 to run the council)'}
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
                      <span>Each persona is answered by the model you assigned to it above (one query per persona). Fast and efficient.</span>
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
                      <span>Every distinct model assigned across the personas above answers from every persona's perspective. Multiplies API cost/time, but gives complete comparative coverage.</span>
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
                  disabled={!isWeightValid}
                  title={!isWeightValid ? 'Persona weights must sum to 1.00' : undefined}
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
