# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

There is also an optional **Persona Council mode** (a Stage 0 added on top of the standard flow) where the Chairman model first proposes 3 expert personas/perspectives for the query, and council members answer from those perspectives instead of generically. See "Persona Mode" below.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers) — this is the fixed set queried in **Standard mode**
- Contains `PERSONA_MODEL_CHOICES`: a separate, larger list of `{id, tier}` dicts (`tier` is a coarse OpenRouter pricing bucket: `low` < $1/M blended tokens, `medium` $1-$10, `max` > $10) used to populate the per-persona model dropdown in **Persona mode**. Changing this list does not affect Standard mode. Served to the frontend via `GET /api/available-models`.
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic
- Persona dicts carry both a text field `weightage` (free-text focus/instructions, shown in the Stage1 system prompt) and a separate numeric `weight` (0-1, all personas' weights should sum to 1 — see Stage 3 below) plus a `model` field (an OpenRouter id from `PERSONA_MODEL_CHOICES`, chosen per-persona by the user in the UI). Don't confuse `weightage` (text) with `weight` (number) — they're independent fields serving different prompts.
- `stage1_collect_responses(user_query, mode, personas, mapping_option)`: Parallel queries to all council models
  - Standard mode (`mode != "persona"`): one plain user-message query per council model
  - Persona mode (`mode == "persona"`, requires `personas`): each query gets a `STAGE1_PERSONA_SYSTEM_PROMPT` system message built from a persona's `name`/`weightage`/`facets`. Each persona is queried against **its own assigned `model`** (defaults to round-robin over `COUNCIL_MODELS` if a persona has no `model` set, e.g. old callers like the smoke test). Two distribution strategies via `mapping_option`:
    - `"round_robin"` (Option C, default): one query per persona, sent to that persona's assigned model → query count == number of personas (3 by default), NOT tied to `len(COUNCIL_MODELS)`
    - `"matrix"` (Option B): every *distinct* model assigned across the personas answers from every persona's perspective → `len(personas) * len(distinct assigned models)` queries — no longer a fixed 12, since the model set is now user-chosen per persona
  - Each Stage 1 result includes `persona_weight` (copied from the persona's numeric `weight`) alongside `model`/`persona`/`response`, for use in Stage 3.
- `stage2_collect_rankings(user_query, stage1_results, mode, council_models=None)`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization (in persona mode, model names are suffixed with `(persona name)`)
  - Prompts models to evaluate and rank (with strict format requirements); uses `STAGE2_PERSONA_RANKING_PROMPT` instead of `STAGE2_STANDARD_RANKING_PROMPT` when `mode == "persona"`
  - `council_models` param controls which models perform the ranking; defaults to the full `COUNCIL_MODELS` when omitted. **In persona mode, callers (`main.py`'s streaming endpoint and `run_full_council()`) pass the deduplicated set of models actually used in Stage 1** (`dict.fromkeys(r['model'] for r in stage1_results)`), not the static `COUNCIL_MODELS` list — this matters now that persona mode can use arbitrary user-chosen models that may not even be in `COUNCIL_MODELS`.
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes both raw text and `parsed_ranking` list
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings; uses `STAGE3_PERSONA_CHAIRMAN_PROMPT` in persona mode, which now surfaces each persona's numeric `Weight` (0-1) to the chairman and explicitly instructs it to proportionally emphasize higher-weighted perspectives (while still substantively addressing lower-weighted ones) when resolving trade-offs/conflicts between perspectives
- `suggest_personas(user_query)`: Stage 0 for persona mode. Always calls `google/gemini-2.5-flash` (hardcoded, independent of `CHAIRMAN_MODEL`) with `PERSONA_SUGGESTION_PROMPT`, expects a JSON object with exactly 3 personas (`name`, `weightage`, `facets`). Falls back to 3 hardcoded default personas (Technical Architect / UX Designer / Product & Cost Analyst) if the call fails or JSON parsing fails. Does NOT set `model`/`weight` — the frontend fills those in with defaults (see `ChatInterface.jsx` below) after the API call returns.
- `generate_conversation_title(user_query)`: Also hardcoded to `google/gemini-2.5-flash`. Generates a 3-5 word title from the first user message; truncates to 50 chars; falls back to "New Conversation" on failure.
- `run_full_council()`: Non-streaming convenience wrapper that runs stages 1→3 sequentially and returns `(stage1_results, stage2_results, stage3_result, metadata)`. The streaming endpoint in `main.py` does NOT call this — it calls the individual stage functions directly so it can emit SSE events between stages. Both paths independently compute and pass the same deduplicated `council_models` into Stage 2 for persona mode.
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
- `delete_conversation(conversation_id)`: removes the conversation's JSON file from disk; returns `False` if it didn't exist (used by `DELETE /api/conversations/{id}`)

**`main.py`**
- FastAPI app with CORS enabled for all origins (`allow_origins=["*"]`)
- POST `/api/conversations/{id}/message`: blocking endpoint, calls `run_full_council()`, returns `{stage1, stage2, stage3, metadata}` in one response
- POST `/api/conversations/{id}/message/stream`: **primary endpoint used by the frontend.** Server-Sent Events; runs each stage as an `asyncio.Task` and yields `: keep-alive` comments every 2s while waiting so the connection doesn't time out. Event sequence: `stage1_start` → `stage1_complete` → `stage2_start` → `stage2_complete` (includes `label_to_model`/`aggregate_rankings` in `metadata`) → `stage3_start` → `stage3_complete` → (`title_complete` if first message) → `complete`. Emits `error` event and stops on exception. Saves the full assistant message (with metadata) to storage only after all stages finish. In persona mode, computes the deduplicated Stage 1 model set and passes it as `council_models` into `stage2_collect_rankings()` (see `council.py` notes above).
- DELETE `/api/conversations/{id}`: removes a conversation via `storage.delete_conversation()`; 404 if not found
- GET `/api/available-models`: returns `{council_models: PERSONA_MODEL_CHOICES}` — powers the per-persona model dropdown on the frontend
- POST `/api/suggest-personas`: calls `suggest_personas()`, used by the frontend's persona-mode Step 1→2 transition
- Request body for both message endpoints: `{content, mode: "standard"|"persona", personas: [...]|null, mapping_option: "round_robin"|"matrix"}`

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- `handleSendMessage()` drives the SSE stream (via `api.sendMessageStream`) and progressively patches the in-flight assistant message's `stage1`/`stage2`/`stage3`/`metadata`/`loading` fields as each SSE event arrives — this is what powers the per-stage spinners in the UI
- Metadata received over SSE is stored in UI state for display AND is persisted backend-side (see `storage.py` note above)
- `handleDeleteConversation()`: calls `api.deleteConversation()`, removes the conversation from local state, and clears `currentConversationId` if the deleted conversation was the active one

**`api.js`**
- `sendMessageStream()` manually parses the SSE response body (`ReadableStream` + `TextDecoder`), buffering partial lines and dispatching `onEvent(type, event)` for each `data: ...` line
- Also exposes non-streaming `sendMessage()` (hits `/message`) and `suggestPersonas()` (hits `/api/suggest-personas`), though the UI only uses the streaming path for sending messages
- `deleteConversation()` (DELETE `/api/conversations/{id}`) and `getAvailableModels()` (GET `/api/available-models`)

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding
- Drives the **Persona Council mode flow**: mode selector (Standard vs Persona) is only shown for the first message in a conversation. In persona mode: Step 1 (enter query) → "Suggest Personas" button calls `api.suggestPersonas()` → Step 2 shows editable persona cards (name/weightage/facets, **plus per-persona model dropdown and numeric weight input**) and a round-robin vs matrix radio choice → "Run Council" calls `onSendMessage` with `{mode: 'persona', personas, mappingOption}`
- Loads `api.getAvailableModels()` on mount into `availableModels` state; the model `<select>` groups options into `<optgroup>`s by cost tier (Low/Medium/Max, from `PERSONA_MODEL_CHOICES`' `tier` field)
- `withDefaults()`: when personas come back from `suggestPersonas()`, fills in a default `model` (round-robins over `availableModels`) and a default numeric `weight` (evenly split across personas, e.g. 0.33/0.33/0.34) for any persona missing one — user edits from there
- Weight validation: `isWeightValid` requires all personas' `weight` fields to sum to 1.00 (±0.01); "Run Council" is disabled and the total-weight display turns red/invalid until it does
- Once a conversation has its first message, mode/personas are locked in for that conversation — only the first message can choose mode

**`components/Sidebar.jsx`**
- Each conversation row has a delete (`×`) button; `window.confirm()` before calling `onDeleteConversation(conv.id)` (wired to `App.jsx`'s `handleDeleteConversation`). Click is `stopPropagation()`-ed so it doesn't also trigger conversation selection.

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
1. Score each response 1-5 on three criteria (accuracy/correctness, depth & completeness,
   actionability/practical value), each with a one-line justification
2. Explicit anti-bias instruction: don't favor length/elaborate style over substance, and
   don't assume/favor any response as "your own" even though anonymized
3. Provide "FINAL RANKING:" header, informed by the scoring above
4. Numbered list format: "1. Response C", "2. Response A", etc.
5. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations. The three named criteria and their exact wording live in `STAGE2_STANDARD_RANKING_PROMPT`/`STAGE2_PERSONA_RANKING_PROMPT` in `prompts.py` — edit there, not `council.py`, to tweak the rubric.

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
5. **Matrix mode cost**: persona mode with `mapping_option: "matrix"` multiplies Stage 1 queries to `len(personas) * len(distinct models assigned across personas)` — since models are now user-chosen per persona (not the fixed `COUNCIL_MODELS`), this is no longer a fixed number (previously 12) and can be larger or smaller depending on how many distinct models the user picks — worth flagging to users before they pick it
6. **Persona `weight` must sum to 1.00**: the frontend blocks "Run Council" until the numeric `weight` fields across all persona cards sum to 1.00 (±0.01); if you're constructing persona payloads outside the UI (e.g. via the API directly or in `scratch/test_persona_council.py`), remember to set both `weight` (numeric) and `model` yourself — `suggest_personas()` doesn't set either

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
[Persona mode only] Stage 0: suggest_personas() → 3 personas (name/weightage/facets), user assigns a model
                    + numeric weight to each and edits in UI (frontend fills sensible defaults)
    ↓
Stage 1: Parallel queries → [individual responses]
         (standard: 1 query/model | persona round-robin: 1 query/persona, sent to that persona's assigned
          model | persona matrix: personas × distinct assigned models)
    ↓
Stage 2: Anonymize → Parallel ranking queries (ranked by the deduplicated set of models actually used
          in Stage 1, in persona mode) → [evaluations + parsed rankings]
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
