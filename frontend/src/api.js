/**
 * API client for the LLM Council backend.
 */

const API_BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * List the council models available for selection.
   */
  async getAvailableModels() {
    const response = await fetch(`${API_BASE}/api/available-models`);
    if (!response.ok) {
      throw new Error('Failed to load available models');
    }
    return response.json();
  },

  /**
   * Suggest 3 expert personas for a prompt.
   */
  async suggestPersonas(content) {
    const response = await fetch(`${API_BASE}/api/suggest-personas`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) {
      throw new Error('Failed to suggest personas');
    }
    return response.json();
  },

  /**
   * Upload a file and extract its text content for use as an attachment.
   * @param {File} file - The file to extract
   * @returns {Promise<{file_name, extracted_text, truncated, file_type}>}
   */
  async extractFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    // No Content-Type header — browser sets the multipart boundary automatically
    const response = await fetch(`${API_BASE}/api/extract-file`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to extract file');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {string} mode - The mode ('standard' or 'persona')
   * @param {Array} personas - The list of custom personas
   * @param {string} mappingOption - Model mapping option ('round_robin' or 'matrix')
   * @param {string} chairmanModel - Model for Stage 3 synthesis ('' = backend default)
   * @param {Object|null} attachment - {file_name, extracted_text} or null
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, mode, personas, mappingOption, chairmanModel, attachment, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          mode,
          personas,
          mapping_option: mappingOption,
          chairman_model: chairmanModel || null,
          attachment: attachment || null,
        }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (value) {
          buffer += decoder.decode(value, { stream: true });
        } else if (done) {
          buffer += decoder.decode();
        }

        const lines = buffer.split('\n');
        // Keep the last item in the buffer (which is incomplete until the next chunk)
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const data = trimmed.slice(6);
            try {
              const event = JSON.parse(data);
              onEvent(event.type, event);
            } catch (e) {
              console.error('Failed to parse SSE event:', e, 'Line:', line);
            }
          }
        }

        if (done) {
          // Process any leftover content in the buffer
          const trimmed = buffer.trim();
          if (trimmed.startsWith('data: ')) {
            const data = trimmed.slice(6);
            try {
              const event = JSON.parse(data);
              onEvent(event.type, event);
            } catch (e) {
              console.error('Failed to parse final SSE event:', e, 'Buffer:', buffer);
            }
          }
          break;
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};
