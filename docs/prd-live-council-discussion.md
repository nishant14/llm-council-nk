# PRD: Live Council Discussion (Interactive Persona Deliberation)

**Status:** Draft v1
**Author:** Nishant (concept) / drafted with Claude
**Date:** 2026-07-02
**Relationship to existing product:** A new, third mode alongside Standard and Persona Council. It reuses the existing OpenRouter plumbing, persona suggestion (Stage 0), storage, and SSE infrastructure, but replaces the batch "answer → rank → synthesize" pipeline with a **turn-by-turn, chairman-moderated live discussion** that the user watches unfold and can join at any moment.

---

## 1. Vision

Today, LLM Council is a black box between "Send" and "final answer": personas answer in parallel, never see each other's arguments until the anonymized ranking stage, and the user has no way to steer once the run starts.

Real organizational decisions don't work that way. In a real meeting:

- A **chair** frames the problem, breaks it into discussion points, and keeps order.
- Each point is **led by the person whose expertise it touches most**.
- Others speak **only where their view genuinely conflicts or adds something** — not everyone repeats everything.
- People **respond to each other**, concede, push back, and converge on a compromise that is best for the organization, not for any one function.
- The meeting ends with **decisions, action items, and owners** — not an essay.
- Anyone in the room (especially the sponsor) can **interject at any time** with new context, an opinion, or a priority override, and the discussion adapts.

**Live Council Discussion replicates this.** The user poses a problem, confirms the cast of expert personas and their focus areas, approves the agenda the chairman drafts, and then watches a live chat where personas debate each agenda point under the chairman's moderation — with the user able to intervene at any turn. The output is a decision document: per-point resolutions, an overall recommendation, action items, and follow-up tasks.

---

## 2. Goals & Non-Goals

### Goals

1. **Transparency of deliberation.** The user sees *how* the answer was reached — every argument, rebuttal, and concession, in order, attributed to a named persona.
2. **Genuine dialectic.** Personas respond to each other's actual words (not blind parallel answers). Conflict is surfaced deliberately, then resolved.
3. **User participation at any point.** The user can pause, inject context, state their own perspective, override priorities, redirect, skip, or end early — and the discussion visibly incorporates it.
4. **Structured, actionable output.** Every session ends with per-point decisions, an overall recommendation, action items, and follow-up tasks with suggested owners.
5. **Bounded cost and time.** The discussion protocol has explicit turn budgets so a session can't spiral into unbounded token spend.
6. **Confirmation gates.** Nothing expensive runs until the user has confirmed the problem framing, the personas, and the agenda.

### Non-Goals (v1)

- **Not** replacing Standard or Persona Council modes; those remain untouched.
- **No** free-form voice/audio; text chat only.
- **No** true token-level parallel streaming of multiple personas talking simultaneously. Turns are sequential (that's the point of a chaired meeting).
- **No** multi-user sessions; one human participant per discussion.
- **No** anonymized peer ranking inside this mode (Stage 2's anonymization solves a batch-mode bias problem; in a live debate, attribution *is* the feature). The chairman's moderation replaces ranking as the quality mechanism.
- **No** file uploads in v1 (tracked separately in `ideas-scratchpad.md`; the data model should not preclude it).

---

## 3. Key Principles (read these before writing any code)

These are the invariants an implementing AI model must hold across every phase. When a design question comes up that this PRD doesn't answer, resolve it in favor of these principles.

1. **The transcript is the single source of truth.** Every utterance — chairman, persona, or user — is an append-only `TranscriptEntry` with a stable `turn_id`. UI state, prompts, resumption, and export are all derived from the transcript plus the session state record. Never keep discussion state that isn't reconstructible from these two.

2. **The discussion is a state machine, not a script.** The orchestrator advances through explicit named states (§6). Every LLM call happens inside exactly one state, and every state transition is deterministic given (current state, LLM output, pending user interventions). This is what makes the system debuggable, resumable, and testable without a frontend.

3. **One turn = one LLM call = one atomic unit.** A "turn" is the smallest unit of progress. The server generates one turn, appends it, emits it, then checks for interventions and decides the next state. Never batch multiple speaker turns into a single generation — that's how you get the model ventriloquizing a fake debate.

4. **Each persona is played by its own assigned model with only its own knowledge of the room.** A persona's prompt contains: its identity/focus, the problem, confirmed agenda, and the *visible transcript so far* — never another persona's system prompt or the chairman's private moderation reasoning. Distinct models per persona (reusing `PERSONA_MODEL_CHOICES`) keeps voices genuinely different.

5. **The chairman moderates; it does not argue.** Chairman turns are procedural (open a point, invite a speaker, summarize, resolve, adapt to intervention) or synthetic (decisions, action items). If the chairman starts injecting its own substantive opinions mid-debate, that's a prompt bug. The chairman's *moderation decisions* (who speaks next, is this point resolved) are structured JSON outputs, separate from its *spoken* transcript text.

6. **User interventions are turns, and they always win.** An intervention enters the transcript like any other utterance and is processed at the next turn boundary — before any queued persona turn. A priority override from the user is binding on the chairman: it must acknowledge it in its next turn and visibly adjust (re-weight, re-order agenda, redirect the current point). The user is the sponsor in the room; the council advises, the user decides.

7. **Conflict is invited, not defaulted.** After a lead persona presents, the chairman explicitly determines *which* other personas materially disagree or have something to add (via a cheap structured "conflict check" call), and invites only those. "Everyone speaks on everything" recreates the batch mode's redundancy and burns the turn budget.

8. **Everything is budgeted.** Per-point and per-session turn caps (§6.4) are hard limits enforced by the orchestrator, not suggestions in a prompt. When a budget is hit, the chairman is forced into resolution ("we must move on; here is the compromise as I see it").

9. **Degrade gracefully, never silently.** If a persona's model call fails after retry, the chairman notes on the record that the persona is unavailable for that turn and continues. If a structured moderation output fails to parse, fall back to a defined default (§10). Never crash the session; never hide a failure from the transcript.

10. **Confirmation gates are real stops.** Persona review and agenda review are server-side states that block until an explicit user confirmation request arrives. Do not "helpfully" auto-advance after a timeout.

11. **Reuse before rebuild.** `openrouter.py` (async queries), `suggest_personas()` (Stage 0), `PERSONA_MODEL_CHOICES` + `/api/available-models`, the SSE streaming pattern in `main.py`, and JSON storage conventions in `storage.py` all carry over. New logic lives in a new `backend/discussion.py` (orchestrator) and new prompts in `backend/prompts.py`. Standard/Persona mode code paths must not change behavior.

12. **Ship in phases, each independently verifiable.** Follow the build plan in §11. Every phase ends with something runnable (a smoke script or a UI slice) and explicit acceptance criteria. Do not start phase N+1 with phase N's criteria unmet.

---

## 4. User Experience

### 4.1 End-to-end flow

```
Step 1  FRAME      User describes the problem (+ optional context, constraints, org background).
Step 2  PERSONAS   Chairman proposes 3–5 personas with focus areas → user edits/adds/removes/
                   re-weights, assigns models → confirms.                          [GATE]
Step 3  AGENDA     Chairman drafts discussion agenda: 3–7 bullet points, each with a one-line
                   scope and a designated lead persona → user edits/reorders/deletes/adds →
                   confirms.                                                       [GATE]
Step 4  DISCUSS    Live chat. For each agenda point:
                     a. Chairman opens the point, hands to the lead persona.
                     b. Lead persona presents its position (recommendation + reasoning).
                     c. Chairman runs a conflict check; invites personas with material
                        disagreement or additions, one at a time.
                     d. Bounded rebuttal exchange between conflicting personas.
                     e. Chairman states the resolution for the point: the compromise/decision,
                        noted dissent, and any action items it generates.
                   The user can intervene before any turn (see 4.2).
Step 5  SYNTHESIZE Chairman produces the closing package: overall recommendation, per-point
                   decision log, action items (owner, priority, suggested timeline), follow-up
                   tasks / open questions.
Step 6  WRAP       User can ask follow-up questions to the chairman or any persona (bounded
                   Q&A turns), then the session is archived like any conversation.
```

### 4.2 User intervention (the core differentiator)

An intervention composer (text box + type selector) is **always visible** during Step 4. Interventions take effect at the next turn boundary — the currently rendering turn finishes, then the user's message enters the transcript and the chairman's next turn must address it.

| Intervention type | Example | Required chairman behavior |
|---|---|---|
| **Add context** | "FYI: we already have a signed contract with vendor X until 2027." | Acknowledge; restate how it changes the current point; personas see it in transcript from now on. |
| **Own perspective** | "As the founder, I think speed matters more than polish here." | Acknowledge; treat as a strongly-weighted voice in resolution of the current and future points. |
| **Priority override** | "Deprioritize cost — budget is not the constraint. Security is." | Binding. Chairman restates revised priorities, may re-order remaining agenda, and resolutions must reflect the override. |
| **Direct question** | "@Security Architect — does this hold if we're SOC2 audited?" | Chairman gives the floor to that persona for one answer turn, then resumes. |
| **Redirect / skip** | "We've covered this. Move to the next point." | Chairman immediately resolves the current point with what's on record and advances. |
| **Pause / resume** | (button) | No new turns are generated until resume. Step mode (§4.3) is the generalization. |
| **End discussion** | "Wrap it up." | Chairman resolves the current point briefly and jumps to synthesis (Step 5). |

Free text without a selected type defaults to **Add context**; the chairman classifies intent as part of its acknowledgment turn.

### 4.3 Pacing controls

Two modes, switchable at any time:

- **Auto-advance (default):** turns generate continuously with a short (configurable, default ~2s) gap between them so the user can read and has a window to interject. A prominent **Pause** button stops after the current turn.
- **Step mode:** nothing generates until the user clicks **Next turn**. This is also the primary mechanism during development/testing.

Under the hood these are the same thing: the client drives turn generation; auto-advance is the client auto-requesting the next turn (§7.2).

### 4.4 UI sketch (frontend)

- **Main pane — live transcript.** Chat-style bubbles. Chairman turns visually distinct (neutral/system styling, centered or left-anchored with a gavel icon); each persona gets a stable color + avatar initials; user interventions highlighted (e.g. amber border). Markdown rendered via the existing `markdown-content` convention. Auto-scroll with a "jump to latest" affordance when the user has scrolled up.
- **Right rail — agenda tracker.** The confirmed agenda as a checklist: current point highlighted, resolved points show a one-line decision summary (click to expand the full resolution), upcoming points dimmed. Doubles as navigation for reading the transcript.
- **Bottom — intervention composer.** Textarea + type chips (Context / My view / Override / Ask persona / Skip / End) + Pause-Resume/Step controls + turn-budget indicator ("Point 2 of 5 · turn 4/8").
- **Cast strip (top).** Persona chips with name, model, weight; hover for focus area. During Step 2 this is the editable persona card UI (reuse the existing persona-mode cards, including model dropdown grouped by cost tier and weight validation).
- **Decision panel (Step 5).** Rendered as cards: Overall recommendation / Decision log table / Action items table / Follow-ups. Exportable as markdown.

---

## 5. Roles

| Role | Played by | Responsibilities |
|---|---|---|
| **Chairman** | `CHAIRMAN_MODEL` (make selectable per-session in UI; default from config) | Frame agenda; open/close points; pick lead + invited speakers via structured moderation decisions; enforce budgets; integrate interventions; write per-point resolutions; produce final synthesis. Never argues a substantive position of its own. |
| **Persona** (3–5) | Its user-assigned model from `PERSONA_MODEL_CHOICES` | Argue its point of view from its focus area (`weightage` text); present when lead; rebut only when invited; concede when convinced; stay in character; keep turns short (see prompt rules §9). Numeric `weight` informs the chairman's resolutions exactly as in existing persona mode Stage 3. |
| **User** | Human | Sponsor of the decision. Confirms gates, intervenes, ultimately owns the outcome. |

---

## 6. Discussion Protocol (state machine)

### 6.1 Session states

```
CREATED → FRAMING → PERSONA_PROPOSAL → PERSONA_REVIEW ⟲ → AGENDA_PROPOSAL → AGENDA_REVIEW ⟲
        → DISCUSSION → SYNTHESIS → WRAP_QA ⟲ → COMPLETED
   (any state) → ABORTED
```

- `PERSONA_REVIEW` and `AGENDA_REVIEW` loop on user edits ("re-suggest with this feedback" re-invokes the proposal call with the user's notes appended) until an explicit confirm.
- `DISCUSSION` contains a nested per-point machine (6.2), iterated over `agenda[]` in confirmed order.

### 6.2 Per-point states

```
POINT_OPEN            Chairman: 1 turn. Introduces the point, frames what's at stake,
                      hands to lead persona.
LEAD_STATEMENT        Lead persona: 1 turn. Position + reasoning + concrete recommendation.
CONFLICT_CHECK        Chairman: 1 structured (non-transcript) call. Given the lead statement,
                      returns JSON: for each other persona → {stance: agree|conflict|add,
                      one_line_reason}. Personas with "conflict" or "add" go on the speaker
                      queue (conflicts first, ordered by persona weight desc).
INVITED_RESPONSE      Chairman: short handoff turn ("I'll bring in <persona>, who sees a
                      tension here…") THEN invited persona: 1 turn responding to the specific
                      prior statements (quote/reference what they disagree with).
REBUTTAL_LOOP         Chairman decides after each invited response (structured call):
                      {action: invite_reply | next_speaker | resolve}. A persona directly
                      challenged may get 1 reply turn. Loop until speaker queue is empty,
                      convergence is detected, or the point turn-budget is hit.
POINT_RESOLUTION      Chairman: 1 turn + structured record. Spoken summary of the compromise
                      AND a JSON PointResolution: {decision, rationale, dissent: [{persona,
                      position}], action_items: [...], follow_ups: [...]}.
```

### 6.3 Intervention handling (uniform rule)

At every turn boundary the orchestrator drains the intervention queue **before** generating the next planned turn:

1. Append the user's message(s) to the transcript.
2. Generate one chairman `INTERVENTION_ACK` turn that (a) classifies/acknowledges the intervention, (b) states its effect (per the table in §4.2), and (c) for overrides, emits a structured `PriorityUpdate` record stored on the session.
3. Resume the per-point machine — possibly in a modified position (e.g. `skip` jumps to `POINT_RESOLUTION`; `end` jumps to `SYNTHESIS`; a direct question inserts one `INVITED_RESPONSE` for the named persona).

### 6.4 Budgets (defaults, all configurable per session)

| Budget | Default |
|---|---|
| Agenda points | 3–7 (chairman proposes; user gate controls final count) |
| Turns per point (persona turns, excl. chairman procedure) | 8 |
| Reply chain depth per exchange | 2 (statement → rebuttal → reply, then chairman moves on) |
| Persona turn length | ≤ 250 words, enforced by prompt + a max_tokens ceiling |
| Chairman procedural turn length | ≤ 120 words |
| Wrap-up Q&A turns | 10 |
| Session hard cap (total LLM calls incl. structured ones) | 120 |

When a cap forces resolution, the chairman must say so on the record ("in the interest of time…") — honesty about the mechanism builds trust.

---

## 7. Architecture

### 7.1 Backend

New module **`backend/discussion.py`** — the orchestrator:

- `class DiscussionSession` (pydantic or dataclass, serialized to JSON): full state per §8.
- `async def advance(session, user_events: list) -> list[Turn]` — the single entry point: drain interventions, run exactly the state transitions needed to produce the next turn(s) (a chairman handoff + persona response may pair up), persist, return new turns. Pure function of (session, events) apart from LLM calls.
- Structured chairman calls (`CONFLICT_CHECK`, rebuttal-loop decisions, `PointResolution`) use JSON-mode prompting with a strict "return only JSON" contract and a tolerant parser (strip code fences, first `{...}` block) — same defensive style as `parse_ranking_from_text()`.

**`backend/prompts.py`** gains the prompt inventory in §9 (all prompts live here, per existing convention — never inline in the orchestrator).

**`backend/storage.py`** gains a parallel store: `data/discussions/{id}.json` (don't overload the conversations schema; a discussion is a different shape). List/get/delete mirroring conversation functions. Discussions appear in the sidebar alongside conversations, badged as discussions.

**`backend/openrouter.py`** unchanged, except: add optional `max_tokens` param to `query_model()` (turn-length ceilings) if not already supported.

**`backend/config.py`**: add `DISCUSSION_DEFAULTS` (budgets from §6.4), `DISCUSSION_CHAIRMAN_MODEL` (defaults to `CHAIRMAN_MODEL`).

Standard/Persona code paths: **zero behavioral changes.**

### 7.2 Transport: client-driven turns over plain HTTP + SSE per turn

SSE is server→client only, and this feature is fundamentally interactive — so the design inverts control: **the client requests each turn**, and the server streams that single turn back over SSE. This gives step mode for free, makes auto-advance a trivial client loop, makes pause = "stop requesting", and means interventions are ordinary POSTs with no queue-race against a long-lived stream. It also keeps requests short (no 10-minute SSE connections through nginx) and makes every turn independently retryable.

```
POST   /api/discussions                          → create session {problem, context} → session JSON
POST   /api/discussions/{id}/personas/suggest    → chairman persona proposal (reuses Stage-0 machinery,
                                                   with focus areas; accepts optional user feedback for
                                                   re-suggestion)
POST   /api/discussions/{id}/personas/confirm    → body: final personas[] (name, weightage, facets,
                                                   model, weight; weights sum to 1.00 ±0.01 as today)
POST   /api/discussions/{id}/agenda/suggest      → chairman agenda proposal (accepts feedback for
                                                   re-suggestion)
POST   /api/discussions/{id}/agenda/confirm      → body: final agenda[] (ordered points, lead per point)
POST   /api/discussions/{id}/turn                → generate the next turn(s). SSE response:
                                                   turn_start {speaker, type, point_id} →
                                                   (optional) token deltas → turn_complete {TranscriptEntry}
                                                   → state {SessionStateSummary}. Returns state-only if
                                                   session is at a gate or completed. 409 if a turn is
                                                   already generating (idempotency guard).
POST   /api/discussions/{id}/intervene           → body: {type, content, target_persona?}. Queued;
                                                   takes effect on next /turn. Returns updated queue.
POST   /api/discussions/{id}/control             → body: {action: skip_point|end_discussion|abort}
GET    /api/discussions/{id}                     → full session (rehydration/refresh)
GET    /api/discussions                          → list summaries
DELETE /api/discussions/{id}                     → delete
```

Auto-advance: client calls `/turn`, waits `gap_ms` after `turn_complete`, calls again — stopping on pause, gate, or `COMPLETED`. Token-level streaming of the active turn is a should-have (start with whole-turn `turn_complete` events; the SSE shape above already accommodates deltas later).

### 7.3 Context-window strategy

Transcripts grow. Prompts are assembled per-turn from:

1. **Fixed header:** problem statement, user context, confirmed personas roster (names + focus one-liners + weights), agenda, current `PriorityUpdate`s.
2. **Resolved-point summaries:** for each completed point, only its `PointResolution` JSON rendered as 3–4 lines — not the full exchange.
3. **Current point verbatim:** the full transcript of the point under discussion.
4. **Recent interventions verbatim** (they're short and load-bearing).

This keeps per-turn prompt size roughly O(current point + summaries), not O(entire session). The synthesis turn gets all `PointResolution`s plus the decision-relevant interventions, not the raw transcript.

---

## 8. Data Model

```jsonc
// data/discussions/{id}.json
{
  "id": "uuid",
  "created_at": "iso8601",
  "title": "string",                       // generated like conversation titles
  "state": "DISCUSSION",                   // §6.1 states
  "problem": "string",
  "user_context": "string | null",
  "config": { "chairman_model": "...", "budgets": { /* §6.4 */ }, "gap_ms": 2000 },
  "personas": [
    { "id": "p1", "name": "Security Architect", "weightage": "focus text…",
      "facets": ["…"], "model": "openrouter/id", "weight": 0.4, "color": "#…" }
  ],
  "agenda": [
    { "id": "a1", "order": 1, "title": "string", "scope": "one-liner",
      "lead_persona_id": "p1", "status": "resolved|active|pending|skipped",
      "resolution": { "decision": "…", "rationale": "…",
                      "dissent": [{ "persona_id": "p2", "position": "…" }],
                      "action_items": [ /* ids into action_items[] */ ],
                      "follow_ups": ["…"] } | null }
  ],
  "transcript": [
    { "turn_id": 17, "ts": "iso8601", "point_id": "a2",
      "speaker": { "kind": "chairman|persona|user", "persona_id": "p1|null" },
      "type": "point_open|lead_statement|invited_response|rebuttal|handoff|resolution|intervention|intervention_ack|synthesis|qa",
      "content": "markdown",
      "meta": { "model": "openrouter/id", "intervention_type": "override|context|…", "invited_reason": "…" } }
  ],
  "priority_updates": [ { "turn_id": 21, "summary": "Security > cost", "detail": "…" } ],
  "pending_interventions": [ /* drained at next /turn */ ],
  "action_items": [
    { "id": "t1", "point_id": "a1", "description": "…", "owner_persona_id": "p3",
      "owner_hint": "e.g. 'Eng lead'", "priority": "P1", "timeline": "2 weeks" }
  ],
  "synthesis": { "recommendation": "markdown", "decision_log": "derived from agenda resolutions",
                 "follow_ups": ["…"] } | null,
  "call_count": 63                          // against session hard cap
}
```

Persistence: write-through after every turn (same JSON-file style as `storage.py`). A browser refresh rehydrates entirely from `GET /api/discussions/{id}`.

---

## 9. Prompt Inventory (all in `backend/prompts.py`)

| Prompt | Caller | Notes |
|---|---|---|
| `DISCUSSION_PERSONA_SUGGESTION_PROMPT` | personas/suggest | Extends existing Stage-0 prompt: 3–5 personas, each with a *focus area* and *likely stance/bias*; instructed to pick personas whose interests naturally conflict on this problem. Accepts optional user feedback block for re-suggestion. |
| `AGENDA_PROMPT` | agenda/suggest | Given problem + confirmed personas: 3–7 discussion points, each with scope one-liner, designated lead persona (whose expertise it touches most), and a note on where conflict is expected. JSON output. |
| `CHAIR_POINT_OPEN_PROMPT` | POINT_OPEN | Procedural voice; ≤120 words; frame the stakes; hand to lead by name. |
| `PERSONA_TURN_PROMPT` (system) | all persona turns | Identity, focus (`weightage` text), facets; the behavioral contract: stay in character, ≤250 words, reference specific prior statements when disagreeing, concede explicitly when convinced, always land on a concrete position, address colleagues by name, no meta-commentary about being an AI or the format. Turn-specific instruction (present / respond to X / reply to challenge) appended per state. |
| `CHAIR_CONFLICT_CHECK_PROMPT` | CONFLICT_CHECK | JSON-only: stance per non-lead persona given the lead statement. Not spoken; never enters transcript. |
| `CHAIR_FLOW_DECISION_PROMPT` | REBUTTAL_LOOP | JSON-only: {action, next_speaker?, reason}. Includes remaining turn budget so the model can economize. |
| `CHAIR_HANDOFF_PROMPT` | INVITED_RESPONSE | 1–2 sentence spoken handoff, naming the invitee and the tension being explored. |
| `CHAIR_RESOLUTION_PROMPT` | POINT_RESOLUTION | Dual output: spoken summary (compromise best for the organization, weighted by persona `weight` and any `PriorityUpdate`s, dissent noted honestly) + `PointResolution` JSON. |
| `CHAIR_INTERVENTION_ACK_PROMPT` | intervention drain | Classify intent if untyped; acknowledge; state concrete effect; emit `PriorityUpdate` JSON when it's an override. Binding-ness of user overrides is spelled out here. |
| `CHAIR_SYNTHESIS_PROMPT` | SYNTHESIS | From resolutions + priority updates: overall recommendation, decision log, consolidated/deduplicated action items with owners/priority/timeline, follow-up tasks & open questions. |
| `WRAP_QA_PROMPT` | WRAP_QA | Route a user question to chairman or a named persona; answer grounded in the discussion record. |
| `DISCUSSION_TITLE_PROMPT` | after confirm | Reuse `generate_conversation_title()` as-is. |

Formatting contracts that code parses (JSON schemas, the dual spoken+JSON resolution format) live in these prompts — the same edit-in-prompts-not-in-code rule the project already follows for `FINAL RANKING:`.

---

## 10. Failure Handling

| Failure | Behavior |
|---|---|
| Persona model call fails (after 1 retry) | Chairman turn on the record: "<Persona> is unavailable; noting their prior stated position." Point continues. If the *lead* fails on its statement, chairman offers the user (via a gate-like `state` payload) to retry, reassign the persona's model, or skip the point. |
| Chairman structured call unparseable | One re-ask with "return only JSON". Then defaults: CONFLICT_CHECK → invite all non-lead personas in weight order (capped by budget); FLOW_DECISION → `resolve`; PointResolution JSON missing → store spoken text as `decision`, empty structured fields, flag `"degraded": true`. |
| `/turn` while a turn is generating | 409; client treats as "in flight" and re-polls session. |
| Server restart mid-discussion | Session JSON is write-through; rehydrate and continue. A turn that died mid-generation simply never happened (no partial writes). |
| User closes tab | Nothing generates (client-driven turns) — the session naturally freezes and resumes on return. This is a *feature* of the transport choice. |
| Budget exhausted | Forced resolution/synthesis with on-record acknowledgment (§6.4). |
| All models for a point fail | Point marked `skipped` with a transcript note; session continues; surfaced in synthesis follow-ups. |

---

## 11. Build Plan (step-by-step, for an AI implementer)

Each phase is a working increment with acceptance criteria. Do not reorder. Commit per phase.

### Phase 1 — Core orchestrator + state machine (no UI)
- `discussion.py`: session dataclass, state machine (§6.1–6.2), `advance()`, budgets, transcript, JSON persistence in `data/discussions/`.
- All prompts from §9 in `prompts.py`.
- Config additions (§7.1).
- **Smoke script** `scratch/test_live_discussion.py`: creates a session for a canned problem, auto-confirms suggested personas/agenda, loops `advance()` to completion, prints the transcript with speaker labels, prints the synthesis. (Follow the existing `scratch/test_persona_council.py` style; run with `uv run python scratch/test_live_discussion.py`.)
- ✅ *Accept:* smoke script produces a coherent multi-point discussion where personas reference each other's arguments; every point ends with a parseable `PointResolution`; session JSON on disk fully describes the run; budgets demonstrably cap a point (test with budget=2).

### Phase 2 — HTTP API
- All endpoints from §7.2 in `main.py`, including the per-turn SSE response (whole-turn events; no token deltas yet), gates returning state-only, the 409 in-flight guard, and intervention queueing.
- ✅ *Accept:* the full flow is drivable with `curl`/httpie alone: create → suggest/confirm personas → suggest/confirm agenda → repeated `/turn` → completed session with synthesis; an `/intervene` POST between turns visibly changes the chairman's next turn; refreshing via `GET` mid-discussion returns consistent state.

### Phase 3 — Frontend: watchable step-mode discussion
- New discussion flow in the frontend: creation screen (Step 1), persona review reusing existing persona-card UI (Step 2), agenda review (Step 3), transcript view with chairman/persona styling and agenda rail (Step 4, **step mode only**: a "Next turn" button), synthesis panel (Step 5). Sidebar lists discussions.
- ✅ *Accept:* a user can run an entire discussion from the browser clicking "Next turn", with correct attribution, colors, agenda progress, and a rendered decision panel at the end.

### Phase 4 — Interventions + pacing
- Intervention composer with type chips wired to `/intervene`; all seven behaviors from §4.2. Auto-advance loop with configurable gap, Pause/Resume, mode toggle.
- ✅ *Accept:* during auto-advance, submitting a priority override results (within one turn) in a chairman acknowledgment that names the override, and subsequent resolutions reflect it; skip and end-discussion work; pause halts generation within one turn.

### Phase 5 — Wrap-up Q&A, export, resilience polish
- WRAP_QA state + UI; markdown export of transcript + decision package; failure-handling paths from §10 exercised (kill a model id to test degradation); title generation; delete.
- ✅ *Accept:* export produces a self-contained markdown decision document; a persona with an invalid model id degrades per §10 without ending the session.

### Phase 6 — Nice-to-haves (only after 1–5)
- Token-level streaming of the active turn (SSE deltas). Chairman model selectable in UI (also closes the `ideas-scratchpad.md` item). Per-session budget editor. "Re-open point" after resolution. Conflict-heat indicator on the agenda rail.

---

## 12. Cost & Latency Expectations (set user expectations in UI)

Rough per-session call count with defaults (5 points, ~6 persona turns/point average):
- Setup: ~3 calls (personas, agenda, title)
- Per point: 1 open + 1 lead + 1 conflict-check + ~4 invited/rebuttal + ~3 flow-decisions + 1 resolution ≈ 11 → ~55 for 5 points
- Synthesis + acks: ~5
- **Total ≈ 60–70 calls**, most of them short. This exceeds a Persona-mode run (~10 calls) several-fold — the turn-budget indicator and the session hard cap exist precisely for this, and the UI should show a running call count. Structured chairman calls should use a cheap fast model (default the same hardcoded `google/gemini-2.5-flash` used for Stage 0/titles) while *spoken* chairman turns use the chairman model.

Latency per turn ≈ one model call (2–15s). Auto-advance therefore feels like a real chat with people typing — that's desirable, not a bug to optimize away.

---

## 13. Open Questions (decide before/while building; defaults given)

1. **Should personas see each persona's numeric weight?** Default **no** — weights inform only the chairman's resolutions (mirrors existing Stage 3 design; prevents personas from deferring pre-emptively).
2. **Conflict-check visibility.** Default: not in transcript, but keep an inspectable debug record (`meta`) — consistent with the project's "all raw outputs inspectable" transparency principle. Consider a UI toggle later.
3. **Re-opening resolved points via intervention.** Default v1: allowed only as a wrap-up Q&A topic, not a full re-litigation (budget protection). Phase 6 candidate.
4. **Discussions and conversations in one sidebar list or two sections?** Default: one list, type-badged.
5. **Minimum viable persona count.** Default 3 (a 2-persona "discussion" is a debate; still allow it, but the suggestion prompt targets 3–5).

---

## 14. Success Criteria (product-level)

1. A non-technical user can go from problem → confirmed cast → confirmed agenda → watched discussion → decision package without reading docs.
2. In ≥80% of sessions on real prompts, at least one persona *changes or concedes a position* in response to another's argument — the debate is real, not parallel monologues (spot-check qualitatively).
3. A user intervention mid-discussion is acknowledged within one turn and demonstrably alters at least the current point's resolution.
4. Every completed session yields ≥1 action item with an owner and a per-point decision log.
5. No session exceeds its hard call cap; no single model failure ends a session.
