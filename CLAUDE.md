# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

There is also an optional **Persona Council mode** (a Stage 0 added on top of the standard flow) where the Chairman model first proposes 3 expert personas/perspectives for the query, and council members answer from those perspectives instead of generically. See "Persona Mode" below.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic
- `stage1_collect_responses(user_query, mode, personas, mapping_option)`: Parallel queries to all council models
  - Standard mode (`mode != "persona"`): one plain user-message query per council model
  - Persona mode (`mode == "persona"`, requires `personas`): each query gets a `STAGE1_PERSONA_SYSTEM_PROMPT` system message built from a persona's `name`/`weightage`/`facets`. Two distribution strategies via `mapping_option`:
    - `"round_robin"` (Option C, default): each council model gets exactly one persona (`personas[i % len(personas)]`) → same query count as standard mode (4 queries)
    - `"matrix"` (Option B): every model answers from every persona's perspective → `len(personas) * len(COUNCIL_MODELS)` queries (12 with the default config)
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization (in persona mode, model names are suffixed with `(persona name)`)
  - Prompts models to evaluate and rank (with strict format requirements); uses `STAGE2_PERSONA_RANKING_PROMPT` instead of `STAGE2_STANDARD_RANKING_PROMPT` when `mode == "persona"`
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes both raw text and `parsed_ranking` list
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings; uses `STAGE3_PERSONA_CHAIRMAN_PROMPT` in persona mode (explicitly asked to resolve trade-offs/conflicts between perspectives)
- `suggest_personas(user_query)`: Stage 0 for persona mode. Always calls `google/gemini-2.5-flash` (hardcoded, independent of `CHAIRMAN_MODEL`) with `PERSONA_SUGGESTION_PROMPT`, expects a JSON object with exactly 3 personas (`name`, `weightage`, `facets`). Falls back to 3 hardcoded default personas (Technical Architect / UX Designer / Product & Cost Analyst) if the call fails or JSON parsing fails.
- `generate_conversation_title(user_query)`: Also hardcoded to `google/gemini-2.5-flash`. Generates a 3-5 word title from the first user message; truncates to 50 chars; falls back to "New Conversation" on failure.
- `run_full_council()`: Non-streaming convenience wrapper that runs stages 1→3 sequentially and returns `(stage1_results, stage2_results, stage3_result, metadata)`. The streaming endpoint in `main.py` does NOT call this — it calls the individual stage functions directly so it can emit SSE events between stages.
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations

**`prompts.py`**
- Central repository for every prompt template used across the app (no prompts live inline in `council.py`)
- `PERSONA_SUGGESTION_PROMPT`, `CONVERSATION_TITLE_PROMPT`, `STAGE1_PERSONA_SYSTEM_PROMPT`, `STAGE2_STANDARD_RANKING_PROMPT`, `STAGE2_PERSONA_RANKING_PROMPT`, `STAGE3_STANDARD_CHAIRMAN_PROMPT`, `STAGE3_PERSONA_CHAIRMAN_PROMPT`
- When tweaking wording/formatting instructions (e.g. the `FINAL RANKING:` contract that `parse_ranking_from_text()` depends on), edit here, not in `council.py`

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, title, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3, metadata}` — metadata (label_to_model, aggregate_rankings, mode, personas, mapping_option) IS persisted to storage via `add_assistant_message()`, contrary to older assumptions in this file

**`main.py`**
- FastAPI app with CORS enabled for all origins (`allow_origins=["*"]`)
- POST `/api/conversations/{id}/message`: blocking endpoint, calls `run_full_council()`, returns `{stage1, stage2, stage3, metadata}` in one response
- POST `/api/conversations/{id}/message/stream`: **primary endpoint used by the frontend.** Server-Sent Events; runs each stage as an `asyncio.Task` and yields `: keep-alive` comments every 2s while waiting so the connection doesn't time out. Event sequence: `stage1_start` → `stage1_complete` → `stage2_start` → `stage2_complete` (includes `label_to_model`/`aggregate_rankings` in `metadata`) → `stage3_start` → `stage3_complete` → (`title_complete` if first message) → `complete`. Emits `error` event and stops on exception. Saves the full assistant message (with metadata) to storage only after all stages finish.
- POST `/api/suggest-personas`: calls `suggest_personas()`, used by the frontend's persona-mode Step 1→2 transition
- Request body for both message endpoints: `{content, mode: "standard"|"persona", personas: [...]|null, mapping_option: "round_robin"|"matrix"}`

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- `handleSendMessage()` drives the SSE stream (via `api.sendMessageStream`) and progressively patches the in-flight assistant message's `stage1`/`stage2`/`stage3`/`metadata`/`loading` fields as each SSE event arrives — this is what powers the per-stage spinners in the UI
- Metadata received over SSE is stored in UI state for display AND is persisted backend-side (see `storage.py` note above)

**`api.js`**
- `sendMessageStream()` manually parses the SSE response body (`ReadableStream` + `TextDecoder`), buffering partial lines and dispatching `onEvent(type, event)` for each `data: ...` line
- Also exposes non-streaming `sendMessage()` (hits `/message`) and `suggestPersonas()` (hits `/api/suggest-personas`), though the UI only uses the streaming path for sending messages

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding
- Drives the **Persona Council mode flow**: mode selector (Standard vs Persona) is only shown for the first message in a conversation. In persona mode: Step 1 (enter query) → "Suggest Personas" button calls `api.suggestPersonas()` → Step 2 shows editable persona cards (name/weightage/facets) plus a round-robin vs matrix radio choice → "Run Council" calls `onSendMessage` with `{mode: 'persona', personas, mappingOption}`
- Once a conversation has its first message, mode/personas are locked in for that conversation — only the first message can choose mode

**`components/Stage1.jsx`**
- Tab view of individual model responses
- In persona mode, tab labels show `persona (model)` instead of just the model name
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**
- **Critical Feature**: Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display (models receive anonymous labels)
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Aggregate rankings shown with average position and vote count
- Explanatory text clarifies that boldface model names are for readability only

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Sub-path Deployment (nginx reverse proxy)
The app supports being served behind a reverse proxy at a sub-path (default example: `/content/`) — see `docs/nginx-plan.md` for the full design rationale (why a proxied Vite *dev server* can't be path-rewritten with `sub_filter`, and why a production build + native prefix-awareness is the fix).
- `frontend/vite.config.js` sets `base: '/content/'` only when running `vite build` (`npm run dev` stays unprefixed at `/`)
- `frontend/src/api.js` derives `API_BASE` from `import.meta.env.BASE_URL`, so it's `''` in dev and `/content` in the production build — no other frontend code changes needed
- `backend/main.py`:
  - The health check moved from `GET /` to `GET /healthz` — `/` is reserved for serving the built SPA (`frontend/dist`, mounted via `StaticFiles(html=True)` if that directory exists). **Known limitation**: this static mount is not a true wildcard SPA fallback — only the mount root and real files resolve to `index.html`; arbitrary unmatched sub-paths 404. Fine today since the app has no client-side routing, but revisit if that's ever added.
  - Setting the `DEPLOY_PREFIX` env var (e.g. `DEPLOY_PREFIX=/content`) wraps the app in an outer `FastAPI()` mounted at that prefix, so the whole app — API and static frontend alike — natively lives under `/content/...`. This lets nginx do a pure 1:1 `proxy_pass` with zero path rewriting. Unset (local dev default), the app behaves exactly as before.
  - When `DEPLOY_PREFIX` is set, uvicorn is started with `forwarded_allow_ips="*"` so it trusts `X-Forwarded-Proto` from the proxy/tunnel — without this, the first navigation to the bare prefix (no trailing slash) 307-redirects to an `http://` URL and breaks under TLS.
- Production startup: `./start_prod.sh` (builds the frontend, then runs the backend with `DEPLOY_PREFIX` set). `start.sh` remains the dev-mode script and is unaffected.
- nginx must still set `proxy_buffering off`, a generous `proxy_read_timeout` (SSE keep-alives), and forward `X-Forwarded-Proto`/`X-Forwarded-For` — see `docs/nginx-plan.md` for the exact config block.

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models are hardcoded in `backend/config.py`. Chairman can be same or different from council members. The current default is Gemini as chairman per user preference.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware (currently wide open with `allow_origins=["*"]`)
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Persona/title generation are hardcoded to Gemini**: `suggest_personas()` and `generate_conversation_title()` both call `google/gemini-2.5-flash` directly rather than `CHAIRMAN_MODEL` — changing `CHAIRMAN_MODEL` in `config.py` does NOT change which model suggests personas or titles
5. **Matrix mode cost**: persona mode with `mapping_option: "matrix"` multiplies Stage 1 queries to `len(personas) * len(COUNCIL_MODELS)` (12 by default) — worth flagging to users before they pick it on a large council

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling
- Let `suggest_personas`/`generate_conversation_title` use `CHAIRMAN_MODEL` instead of a hardcoded model

## Testing Notes

`scratch/test_persona_council.py` is a manual smoke-test script (not an automated test suite) for the persona flow: it calls `suggest_personas()` then `run_full_council()` in persona/round-robin mode and prints every stage. Run with `uv run python scratch/test_persona_council.py` from the project root. There is no automated test suite (no pytest config, no CI) — verify changes by running this script or exercising the UI directly.

## Data Flow Summary

```
User Query
    ↓ (mode: standard | persona)
[Persona mode only] Stage 0: suggest_personas() → 3 personas (name/weightage/facets), user edits in UI
    ↓
Stage 1: Parallel queries → [individual responses]
         (standard: 1 query/model | persona round-robin: 1 query/model | persona matrix: personas × models)
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Persisted: {stage1, stage2, stage3, metadata} saved to data/conversations/{id}.json
    ↓
Frontend: Display with tabs + validation UI (built up incrementally via SSE events, not a single response)
```

The entire flow is async/parallel where possible to minimize latency. The frontend consumes this via `/message/stream` (SSE), not the blocking `/message` endpoint — see `main.py` notes above.
