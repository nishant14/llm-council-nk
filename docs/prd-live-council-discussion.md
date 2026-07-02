# PRD: Live Council Discussion (Interactive Persona Deliberation)

**Status:** Draft v2
**Author:** Nishant (concept) / drafted with Claude
**Date:** 2026-07-02
**v2 changes:** The former single "Chairman" is split into **two agents** — a **Moderator** (facilitator, strictly neutral) and a **Chair** (adjudicator with delegated decision authority). Added: an explicit decision hierarchy (User > Chair > Personas), a decision contract that prohibits split-the-difference non-decisions, a close-call procedure where divided parties present closing statements before the Chair rules, a "challenge decision" user intervention, and **per-persona briefings** — the user can give any individual persona additional private context via text or file attachments, at setup or mid-discussion.
**Relationship to existing product:** A new, third mode alongside Standard and Persona Council. It reuses the existing OpenRouter plumbing, persona suggestion (Stage 0), storage, and SSE infrastructure, but replaces the batch "answer → rank → synthesize" pipeline with a **turn-by-turn, moderated live discussion** — chaired by an accountable decision-maker — that the user watches unfold and can join at any moment.

---

## 1. Vision

Today, LLM Council is a black box between "Send" and "final answer": personas answer in parallel, never see each other's arguments until the anonymized ranking stage, and the user has no way to steer once the run starts.

Real organizational decisions don't work that way. In a real meeting:

- A **facilitator** frames the problem, breaks it into discussion points, and keeps order.
- Each point is **led by the person whose expertise it touches most**.
- Others speak **only where their view genuinely conflicts or adds something** — not everyone repeats everything.
- People **respond to each other**, concede, push back — and then **someone accountable makes the call**. Disagreement isn't averaged into mush; when the arguments are evenly matched, the chair hears final arguments from the divided parties and then rules.
- The meeting ends with **decisions, action items, and owners** — not an essay.
- Anyone in the room (especially the sponsor) can **interject at any time** with new context, an opinion, or a priority override — and can challenge a decision they think is wrong.

**Live Council Discussion replicates this.** The user poses a problem, confirms the cast of expert personas and their focus areas, approves the agenda, and then watches a live chat where personas debate each agenda point under the Moderator's facilitation — with every point closed by an explicit, on-the-record decision from the Chair, and the user able to intervene at any turn. The output is a decision document: per-point rulings, an overall recommendation, action items, and follow-up tasks.

---

## 2. Goals & Non-Goals

### Goals

1. **Transparency of deliberation.** The user sees *how* the answer was reached — every argument, rebuttal, concession, and ruling, in order, attributed to a named persona or agent.
2. **Genuine dialectic.** Personas respond to each other's actual words (not blind parallel answers). Conflict is surfaced deliberately, argued, and then *decided* — not summarized away.
3. **Accountable decisions.** Every agenda point ends with one committed course of action from the Chair, with rejected alternatives named and dissent recorded. No "both sides have merit" non-decisions.
4. **User participation at any point.** The user can pause, inject context, state their own perspective, override priorities, redirect, skip, challenge a decision, or end early — and the discussion visibly incorporates it. The user can also **brief any individual persona privately** with additional context (text or attached documents), at setup or mid-discussion, the way a sponsor hands an expert the relevant report before a meeting.
5. **Structured, actionable output.** Every session ends with per-point decisions, an overall recommendation, action items, and follow-up tasks with suggested owners.
6. **Bounded cost and time.** The discussion protocol has explicit turn budgets so a session can't spiral into unbounded token spend.
7. **Confirmation gates.** Nothing expensive runs until the user has confirmed the problem framing, the personas, and the agenda.

### Non-Goals (v1)

- **Not** replacing Standard or Persona Council modes; those remain untouched.
- **No** free-form voice/audio; text chat only.
- **No** true token-level parallel streaming of multiple personas talking simultaneously. Turns are sequential (that's the point of a moderated meeting).
- **No** multi-user sessions; one human participant per discussion.
- **No** anonymized peer ranking inside this mode (Stage 2's anonymization solves a batch-mode bias problem; in a live debate, attribution *is* the feature). The Moderator's structured facilitation plus the Chair's accountable, on-the-record adjudication replace ranking as the quality mechanism.
- **No** persona voting or consensus mechanics. Personas advise; the Chair decides; the user can overrule. Voting recreates ranking-by-committee and dodges accountability.
- **No** general chat-wide file context in v1. Attachments are in scope only as **persona briefings** (PDF, plain text, markdown, images — same formats tracked in `ideas-scratchpad.md`); image attachments work only when the persona's assigned model is multimodal (§10). Session-wide file context can build on the same attachment pipeline later.

---

## 3. Key Principles (read these before writing any code)

These are the invariants an implementing AI model must hold across every phase. When a design question comes up that this PRD doesn't answer, resolve it in favor of these principles.

1. **The transcript is the single source of truth.** Every utterance — Moderator, Chair, persona, or user — is an append-only `TranscriptEntry` with a stable `turn_id`. UI state, prompts, resumption, and export are all derived from the transcript plus the session state record. Never keep discussion state that isn't reconstructible from these two.

2. **The discussion is a state machine, not a script.** The orchestrator advances through explicit named states (§6). Every LLM call happens inside exactly one state, and every state transition is deterministic given (current state, LLM output, pending user interventions). This is what makes the system debuggable, resumable, and testable without a frontend.

3. **One turn = one LLM call = one atomic unit.** A "turn" is the smallest unit of progress. The server generates one turn, appends it, emits it, then checks for interventions and decides the next state. Never batch multiple speaker turns into a single generation — that's how you get the model ventriloquizing a fake debate.

4. **Each persona is played by its own assigned model with only its own knowledge of the room.** A persona's prompt contains: its identity/focus, the problem, confirmed agenda, the *visible transcript so far*, and its own **private briefing** (any text/attachments the user has given that persona) — never another persona's system prompt, another persona's briefing, or the Moderator/Chair's private structured reasoning. Briefing *contents* are visible only to that persona; the transcript records that a briefing was delivered, keeping the record honest. Private information enters the debate the same way it does in real life: the briefed expert cites it in their arguments. Distinct models per persona (reusing `PERSONA_MODEL_CHOICES`) keeps voices genuinely different.

5. **Facilitation and adjudication are separate agents with separate contracts.** The **Moderator** runs the debate: procedural spoken turns (open a point, hand off, invite a speaker, acknowledge interventions, convene closing statements) plus structured flow decisions (who speaks next, is this point ready for decision) as JSON outputs distinct from its spoken text. It is strictly neutral — if it expresses a substantive opinion, that's a prompt bug. The **Chair** speaks only at decision moments (point rulings, close-call handling, decision challenges, final synthesis) and must *decide*, not summarize: commit to one course of action, name what was rejected and why, record overruled dissent. **Do not merge these into one prompt** — a single system prompt carrying both "stay neutral" and "make the call" degrades both behaviors. They run as separate agents and may use different models (cheap/fast Moderator, strong Chair); the Chair rules on the record it reads, like a judge, uncontaminated by having produced the moderation itself.

6. **The decision hierarchy is User > Chair > Personas, and user interventions always win.** Personas advise and never vote; the Chair holds delegated decision authority and is accountable for every ruling; the user is the sponsor and holds final authority. An intervention enters the transcript like any other utterance and is processed at the next turn boundary — before any queued turn. A priority override from the user is binding: the Moderator acknowledges it, and every subsequent Chair ruling must reflect it. Rulings are provisional until the session ends — the user can challenge any decision (§4.2), and a reaffirmed challenge stands as a recorded sponsor override.

7. **Conflict is invited, not defaulted.** After a lead persona presents, the Moderator explicitly determines *which* other personas materially disagree or have something to add (via a cheap structured "conflict check" call), and invites only those. "Everyone speaks on everything" recreates the batch mode's redundancy and burns the turn budget.

8. **Close calls get final arguments, then a ruling — never a blend.** Before ruling, the Chair reviews the point's record (structured call). If the decision is genuinely close, it names its key unresolved question and the divided parties each give one closing statement — at most once per point — before the Chair rules. If it's *still* close, the Chair decides anyway, flags the ruling low-confidence/reversible, and generates a validation follow-up task. Splitting the difference to avoid deciding is a prohibited output.

9. **Everything is budgeted.** Per-point and per-session turn caps (§6.4) are hard limits enforced by the orchestrator, not suggestions in a prompt. When a budget is hit, the Chair is forced to rule on what's on the record ("in the interest of time…").

10. **Degrade gracefully, never silently.** If a persona's model call fails after retry, the Moderator notes on the record that the persona is unavailable for that turn and continues. If a structured output fails to parse, fall back to a defined default (§10). Never crash the session; never hide a failure from the transcript.

11. **Confirmation gates are real stops.** Persona review and agenda review are server-side states that block until an explicit user confirmation request arrives. Do not "helpfully" auto-advance after a timeout.

12. **Reuse before rebuild.** `openrouter.py` (async queries), `suggest_personas()` (Stage 0), `PERSONA_MODEL_CHOICES` + `/api/available-models`, the SSE streaming pattern in `main.py`, and JSON storage conventions in `storage.py` all carry over. New logic lives in a new `backend/discussion.py` (orchestrator) and new prompts in `backend/prompts.py`. Standard/Persona mode code paths must not change behavior.

13. **Ship in phases, each independently verifiable.** Follow the build plan in §11. Every phase ends with something runnable (a smoke script or a UI slice) and explicit acceptance criteria. Do not start phase N+1 with phase N's criteria unmet.

---

## 4. User Experience

### 4.1 End-to-end flow

```
Step 1  FRAME      User describes the problem (+ optional context, constraints, org background).
Step 2  PERSONAS   Moderator proposes 3–5 personas with focus areas → user edits/adds/removes/
                   re-weights, assigns models, and optionally gives any persona a private
                   briefing (text and/or attached files) → confirms.               [GATE]
Step 3  AGENDA     Moderator drafts discussion agenda: 3–7 bullet points, each with a one-line
                   scope and a designated lead persona → user edits/reorders/deletes/adds →
                   confirms.                                                       [GATE]
Step 4  DISCUSS    Live chat. For each agenda point:
                     a. Moderator opens the point, frames what's at stake, hands to the lead.
                     b. Lead persona presents its position (recommendation + reasoning).
                     c. Moderator runs a conflict check; invites personas with material
                        disagreement or additions, one at a time.
                     d. Bounded rebuttal exchange between conflicting personas.
                     e. Chair reviews the record. If the call is close, the Moderator convenes
                        closing statements: each divided party gets one final argument addressed
                        to the Chair's stated unresolved question.
                     f. Chair rules on the point, on the record: one committed course of action,
                        rejected alternatives named, dissent recorded (overruled or
                        accommodated), action items captured. Close calls are flagged
                        reversible with a validation follow-up task.
                   The user can intervene before any turn (see 4.2), including challenging a
                   ruling after it's made.
Step 5  SYNTHESIZE Chair produces the closing package: overall recommendation, per-point
                   decision log, action items (owner, priority, suggested timeline), follow-up
                   tasks / open questions, and any sponsor overrides noted.
Step 6  WRAP       User can ask follow-up questions to the Chair or any persona (bounded
                   Q&A turns), then the session is archived like any conversation.
```

### 4.2 User intervention (the core differentiator)

An intervention composer (text box + type selector) is **always visible** during Step 4. Interventions take effect at the next turn boundary — the currently rendering turn finishes, then the user's message enters the transcript and must be addressed in the next turn.

| Intervention type | Example | Required behavior |
|---|---|---|
| **Add context** | "FYI: we already have a signed contract with vendor X until 2027." | Moderator acknowledges; restates how it changes the current point; personas see it in transcript from now on. |
| **Own perspective** | "As the founder, I think speed matters more than polish here." | Moderator acknowledges; the Chair treats it as a strongly-weighted voice in this and future rulings. |
| **Priority override** | "Deprioritize cost — budget is not the constraint. Security is." | Binding. Moderator restates revised priorities and may re-order remaining agenda; every subsequent Chair ruling must reflect the override. |
| **Direct question** | "@Security Architect — does this hold if we're SOC2 audited?" | Moderator gives the floor to that persona for one answer turn, then resumes. |
| **Brief persona** | (to Security Architect) "Here's our latest pen-test report — attached." | Content (text + attachments) is added to that persona's **private briefing** and informs all its future turns. The transcript records that a briefing was delivered (not its contents). No LLM turn is consumed. |
| **Challenge decision** | "That ruling is wrong — we are not dropping vendor X." | The Chair gets one turn to either **revise** the ruling or **defend** it (restating the decisive reasoning). If the user reaffirms the challenge, the user's position stands and is recorded on the resolution as a **sponsor override** — the Chair does not argue further. |
| **Redirect / skip** | "We've covered this. Move to the next point." | Chair immediately rules on the current point with what's on record; Moderator advances. |
| **Pause / resume** | (button) | No new turns are generated until resume. Step mode (§4.3) is the generalization. |
| **End discussion** | "Wrap it up." | Chair rules briefly on the current point and the session jumps to synthesis (Step 5). |

Free text without a selected type defaults to **Add context**; the Moderator classifies intent as part of its acknowledgment turn.

### 4.3 Pacing controls

Two modes, switchable at any time:

- **Auto-advance (default):** turns generate continuously with a short (configurable, default ~2s) gap between them so the user can read and has a window to interject. A prominent **Pause** button stops after the current turn.
- **Step mode:** nothing generates until the user clicks **Next turn**. This is also the primary mechanism during development/testing.

Under the hood these are the same thing: the client drives turn generation; auto-advance is the client auto-requesting the next turn (§7.2).

### 4.4 UI sketch (frontend)

- **Main pane — live transcript.** Chat-style bubbles. Moderator turns styled as neutral/procedural (system-like, gavel icon). **Chair rulings render as inline decision cards** — visually heavier than chat bubbles, showing the decision, rejected alternatives, recorded dissent, and confidence/reversibility flags (plus a sponsor-override badge if challenged and reaffirmed). Each persona gets a stable color + avatar initials; user interventions highlighted (e.g. amber border). Markdown rendered via the existing `markdown-content` convention. Auto-scroll with a "jump to latest" affordance when the user has scrolled up.
- **Right rail — agenda tracker.** The confirmed agenda as a checklist: current point highlighted, resolved points show a one-line ruling summary (click to expand the full decision card), upcoming points dimmed. Doubles as navigation for reading the transcript.
- **Bottom — intervention composer.** Textarea + type chips (Context / My view / Override / Ask persona / Brief persona / Challenge / Skip / End) + attachment button when a persona target is selected + Pause-Resume/Step controls + turn-budget indicator ("Point 2 of 5 · turn 4/8").
- **Cast strip (top).** Moderator and Chair identity chips (with their models), then persona chips with name, model, weight, and a briefing indicator (📎 count) when the persona has been briefed; hover for focus area. During Step 2 this is the editable persona card UI (reuse the existing persona-mode cards, including model dropdown grouped by cost tier and weight validation) **plus a per-persona briefing section: free-text field and file attach (PDF/txt/md/images)**. Clicking a persona chip mid-discussion opens its briefing for additions.
- **Decision panel (Step 5).** Rendered as cards: Overall recommendation / Decision log table / Action items table / Follow-ups / Sponsor overrides. Exportable as markdown.

---

## 5. Roles

| Role | Played by | Responsibilities |
|---|---|---|
| **Moderator** (facilitator) | `DISCUSSION_MODERATOR_MODEL` — default `google/gemini-2.5-flash` (cheap + fast; also runs all structured flow calls) | Propose personas and agenda; open points; pick lead + invited speakers via structured decisions; enforce budgets; acknowledge, classify, and route interventions; convene closing statements. **Strictly neutral — never expresses a substantive opinion and never decides anything substantive.** |
| **Chair** (adjudicator) | `DISCUSSION_CHAIR_MODEL` — default `CHAIRMAN_MODEL`, selectable per session in the UI | Speaks only at decision moments. Reviews each point's record; calls for closing statements when the decision is close; then **rules**: one committed course of action, rejected alternatives named with reasons, dissent recorded as overruled or accommodated, confidence and reversibility flagged. Responds to decision challenges (revise or defend once). Produces the final synthesis. Accountable for every ruling; overrideable only by the user. |
| **Persona** (3–5) | Its user-assigned model from `PERSONA_MODEL_CHOICES` | Argue its point of view from its focus area (`weightage` text); present when lead; rebut only when invited; give a closing statement when convened; concede when convinced; stay in character; keep turns short (§9). **Advisors only — personas never vote.** Numeric `weight` is an input to the Chair's judgment, not a ballot. |
| **User** | Human | Sponsor of the decision and **final authority**: confirms gates, intervenes, sets binding priorities, can challenge and override any ruling, ultimately owns the outcome. |

**Decision hierarchy: User (sponsor) > Chair (delegated decider) > Personas (advisors).** This ordering is stated in the Chair's and Moderator's prompts and enforced by the intervention rules in §4.2/§6.3.

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
POINT_OPEN            Moderator: 1 turn. Introduces the point, frames what's at stake,
                      hands to lead persona.
LEAD_STATEMENT        Lead persona: 1 turn. Position + reasoning + concrete recommendation.
CONFLICT_CHECK        Moderator: 1 structured (non-transcript) call. Given the lead statement,
                      returns JSON: for each other persona → {stance: agree|conflict|add,
                      one_line_reason}. Personas with "conflict" or "add" go on the speaker
                      queue (conflicts first, ordered by persona weight desc).
INVITED_RESPONSE      Moderator: short handoff turn ("I'll bring in <persona>, who sees a
                      tension here…") THEN invited persona: 1 turn responding to the specific
                      prior statements (quote/reference what they disagree with).
REBUTTAL_LOOP         Moderator decides after each invited response (structured call):
                      {action: invite_reply | next_speaker | to_chair}. A persona directly
                      challenged may get 1 reply turn. Loop until speaker queue is empty,
                      convergence is detected, or the point turn-budget is hit — then hand
                      to the Chair.
DECISION_REVIEW       Chair: 1 structured (non-transcript) call over the point's record.
                      Returns JSON: {closeness: clear|close, leaning, key_unresolved_question,
                      divided_parties: [persona_ids]}. "close" triggers CLOSING_STATEMENTS
                      (at most once per point); "clear" goes straight to POINT_RULING.
CLOSING_STATEMENTS    Only on a close call. Moderator announces closing statements and states
                      the Chair's key unresolved question on the record. Each divided party
                      (max 2 personas) gets exactly 1 final turn: strongest remaining argument,
                      a direct answer to the Chair's question, and what they would concede.
                      No new topics. Then to POINT_RULING.
POINT_RULING          Chair: 1 spoken turn + structured record, under the decision contract:
                        • Commit to ONE course of action. "It depends", conditional hedges,
                          and split-the-difference blends are prohibited outputs.
                        • Name the rejected alternative(s) and why they lost.
                        • Record dissent explicitly: each dissenting persona's position, marked
                          overruled or accommodated.
                        • Tie-breaking order: user priority overrides > persona numeric
                          weights > Chair's judgment.
                        • If still close after closing statements: rule anyway, flag the ruling
                          low-confidence + reversible, and generate a validation follow-up task
                          (e.g. "run a 2-week spike before committing").
                      JSON PointResolution schema in §8.
```

### 6.3 Intervention handling (uniform rule)

At every turn boundary the orchestrator drains the intervention queue **before** generating the next planned turn:

1. Append the user's message(s) to the transcript.
2. Generate one Moderator `INTERVENTION_ACK` turn that (a) classifies/acknowledges the intervention, (b) states its effect (per the table in §4.2), and (c) for overrides, emits a structured `PriorityUpdate` record stored on the session (binding on all subsequent Chair rulings).
3. Resume the per-point machine — possibly in a modified position:
   - `skip` jumps to `POINT_RULING`;
   - `end` forces a brief `POINT_RULING` then jumps to `SYNTHESIS`;
   - a direct question inserts one `INVITED_RESPONSE` for the named persona;
   - `brief_persona` appends to the target persona's `briefing` and writes a delivery-stub
     transcript entry ("User briefed <persona>") — no LLM call, no Moderator ack turn;
   - **`challenge`** (targets a resolved point) inserts one Chair turn: revise the ruling (updating its `PointResolution`) or defend it once. A reaffirmed challenge writes a `sponsor_override` onto the resolution and the discussion moves on — the Chair does not re-argue.

### 6.4 Budgets (defaults, all configurable per session)

| Budget | Default |
|---|---|
| Agenda points | 3–7 (Moderator proposes; user gate controls final count) |
| Turns per point (persona turns, excl. procedure) | 8 |
| Reply chain depth per exchange | 2 (statement → rebuttal → reply, then Moderator moves on) |
| Closing-statement rounds per point | 1 round max; max 2 personas, 1 turn each |
| Challenge exchanges per resolved point | 1 (revise-or-defend, then sponsor override applies) |
| Persona turn length | ≤ 250 words, enforced by prompt + a max_tokens ceiling |
| Moderator procedural turn length | ≤ 120 words |
| Chair ruling turn length | ≤ 300 words (spoken part; the JSON record is separate) |
| Wrap-up Q&A turns | 10 |
| Session hard cap (total LLM calls incl. structured ones) | 130 |

When a cap forces a ruling, the Chair must say so on the record ("in the interest of time…") — honesty about the mechanism builds trust.

---

## 7. Architecture

### 7.1 Backend

New module **`backend/discussion.py`** — the orchestrator:

- `class DiscussionSession` (pydantic or dataclass, serialized to JSON): full state per §8.
- `async def advance(session, user_events: list) -> list[Turn]` — the single entry point: drain interventions, run exactly the state transitions needed to produce the next turn(s) (a Moderator handoff + persona response may pair up), persist, return new turns. Pure function of (session, events) apart from LLM calls.
- Structured calls (`CONFLICT_CHECK`, flow decisions, `DECISION_REVIEW`, `PointResolution`) use JSON-mode prompting with a strict "return only JSON" contract and a tolerant parser (strip code fences, first `{...}` block) — same defensive style as `parse_ranking_from_text()`.

**`backend/prompts.py`** gains the prompt inventory in §9 (all prompts live here, per existing convention — never inline in the orchestrator).

**`backend/storage.py`** gains a parallel store: `data/discussions/{id}.json` (don't overload the conversations schema; a discussion is a different shape). List/get/delete mirroring conversation functions. Discussions appear in the sidebar alongside conversations, badged as discussions.

**`backend/openrouter.py`** unchanged, except: add optional `max_tokens` param to `query_model()` (turn-length ceilings) if not already supported.

**`backend/config.py`**: add `DISCUSSION_DEFAULTS` (budgets from §6.4), `DISCUSSION_MODERATOR_MODEL` (default `google/gemini-2.5-flash`), `DISCUSSION_CHAIR_MODEL` (default `CHAIRMAN_MODEL`). Both agent models are per-session overridable; the same model id in both slots is allowed — the separation is in the prompts and call structure, not the weights.

Standard/Persona code paths: **zero behavioral changes.**

### 7.2 Transport: client-driven turns over plain HTTP + SSE per turn

SSE is server→client only, and this feature is fundamentally interactive — so the design inverts control: **the client requests each turn**, and the server streams that single turn back over SSE. This gives step mode for free, makes auto-advance a trivial client loop, makes pause = "stop requesting", and means interventions are ordinary POSTs with no queue-race against a long-lived stream. It also keeps requests short (no 10-minute SSE connections through nginx) and makes every turn independently retryable.

```
POST   /api/discussions                          → create session {problem, context} → session JSON
POST   /api/discussions/{id}/personas/suggest    → Moderator persona proposal (reuses Stage-0
                                                   machinery, with focus areas; accepts optional user
                                                   feedback for re-suggestion)
POST   /api/discussions/{id}/personas/confirm    → body: final personas[] (name, weightage, facets,
                                                   model, weight, briefing text; weights sum to
                                                   1.00 ±0.01 as today)
POST   /api/discussions/{id}/personas/{pid}/briefing
                                                 → multipart: {text?, files[]?} (PDF/txt/md/images).
                                                   Usable at Step 2 and mid-discussion (mid-discussion
                                                   it also enqueues a brief_persona event so the
                                                   delivery stub lands in the transcript). Text is
                                                   extracted from PDF/txt/md at upload time; images
                                                   are stored for multimodal pass-through.
POST   /api/discussions/{id}/agenda/suggest      → Moderator agenda proposal (accepts feedback for
                                                   re-suggestion)
POST   /api/discussions/{id}/agenda/confirm      → body: final agenda[] (ordered points, lead per point)
POST   /api/discussions/{id}/turn                → generate the next turn(s). SSE response:
                                                   turn_start {speaker, type, point_id} →
                                                   (optional) token deltas → turn_complete {TranscriptEntry}
                                                   → state {SessionStateSummary}. Returns state-only if
                                                   session is at a gate or completed. 409 if a turn is
                                                   already generating (idempotency guard).
POST   /api/discussions/{id}/intervene           → body: {type, content, target_persona?,
                                                   target_point?}   // target_persona for direct
                                                   questions & text-only briefings; target_point for
                                                   challenges. Queued; takes effect on next /turn.
                                                   Returns updated queue.
POST   /api/discussions/{id}/control             → body: {action: skip_point|end_discussion|abort}
GET    /api/discussions/{id}                     → full session (rehydration/refresh)
GET    /api/discussions                          → list summaries
DELETE /api/discussions/{id}                     → delete
```

Auto-advance: client calls `/turn`, waits `gap_ms` after `turn_complete`, calls again — stopping on pause, gate, or `COMPLETED`. Token-level streaming of the active turn is a should-have (start with whole-turn `turn_complete` events; the SSE shape above already accommodates deltas later).

### 7.3 Context-window strategy

Transcripts grow. Prompts are assembled per-turn from:

1. **Fixed header:** problem statement, user context, confirmed personas roster (names + focus one-liners + weights, weights visible to Moderator/Chair only — see §13), agenda, current `PriorityUpdate`s. For persona turns only: that persona's own private briefing (extracted text inline; image attachments passed as model inputs when the persona's model is multimodal).
2. **Resolved-point summaries:** for each completed point, only its `PointResolution` JSON rendered as 3–4 lines — not the full exchange.
3. **Current point verbatim:** the full transcript of the point under discussion.
4. **Recent interventions verbatim** (they're short and load-bearing).

This keeps per-turn prompt size roughly O(current point + summaries), not O(entire session). The synthesis turn gets all `PointResolution`s plus the decision-relevant interventions and sponsor overrides, not the raw transcript.

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
  "config": { "moderator_model": "...", "chair_model": "...",
              "budgets": { /* §6.4 */ }, "gap_ms": 2000 },
  "personas": [
    { "id": "p1", "name": "Security Architect", "weightage": "focus text…",
      "facets": ["…"], "model": "openrouter/id", "weight": 0.4, "color": "#…",
      "briefing": {
        "text": "user-provided private context | ''",
        "attachments": [ { "id": "f1", "filename": "pentest-2026.pdf", "mime": "application/pdf",
                           "extracted_text": "…|null" } ]   // files on disk under
      } }                                                    // data/discussions/{id}/attachments/
  ],
  "agenda": [
    { "id": "a1", "order": 1, "title": "string", "scope": "one-liner",
      "lead_persona_id": "p1", "status": "resolved|active|pending|skipped",
      "resolution": {
        "decision": "the ONE committed course of action",
        "rationale": "…",
        "rejected_alternatives": [ { "option": "…", "reason": "…" } ],
        "dissent": [ { "persona_id": "p2", "position": "…",
                       "disposition": "overruled|accommodated" } ],
        "confidence": "high|low",
        "reversible": true,
        "closing_statements_held": false,
        "sponsor_override": { "turn_id": 41, "summary": "…" } | null,
        "action_items": [ /* ids into action_items[] */ ],
        "follow_ups": ["…"]
      } | null }
  ],
  "transcript": [
    { "turn_id": 17, "ts": "iso8601", "point_id": "a2",
      "speaker": { "kind": "moderator|chair|persona|user", "persona_id": "p1|null" },
      "type": "point_open|lead_statement|invited_response|rebuttal|handoff|closing_statement|ruling|challenge_response|intervention|intervention_ack|briefing_delivered|synthesis|qa",
      "content": "markdown",
      "meta": { "model": "openrouter/id", "intervention_type": "override|context|challenge|…",
                "invited_reason": "…" } }
  ],
  "priority_updates": [ { "turn_id": 21, "summary": "Security > cost", "detail": "…" } ],
  "pending_interventions": [ /* drained at next /turn */ ],
  "action_items": [
    { "id": "t1", "point_id": "a1", "description": "…", "owner_persona_id": "p3",
      "owner_hint": "e.g. 'Eng lead'", "priority": "P1", "timeline": "2 weeks" }
  ],
  "synthesis": { "recommendation": "markdown", "decision_log": "derived from agenda resolutions",
                 "sponsor_overrides": [ /* derived */ ], "follow_ups": ["…"] } | null,
  "call_count": 63                          // against session hard cap
}
```

Structured non-transcript calls (`CONFLICT_CHECK`, flow decisions, `DECISION_REVIEW`) are stored in a `debug_records` array on the session — not shown in the transcript UI by default, but inspectable, consistent with the project's "all raw outputs inspectable" transparency principle.

Persistence: write-through after every turn (same JSON-file style as `storage.py`). A browser refresh rehydrates entirely from `GET /api/discussions/{id}`.

---

## 9. Prompt Inventory (all in `backend/prompts.py`)

Moderator prompts are prefixed `MOD_`, Chair prompts `CHAIR_` — two distinct agents, never one merged persona.

| Prompt | Caller | Notes |
|---|---|---|
| `DISCUSSION_PERSONA_SUGGESTION_PROMPT` | personas/suggest (Moderator) | Extends existing Stage-0 prompt: 3–5 personas, each with a *focus area* and *likely stance/bias*; instructed to pick personas whose interests naturally conflict on this problem. Accepts optional user feedback block for re-suggestion. |
| `AGENDA_PROMPT` | agenda/suggest (Moderator) | Given problem + confirmed personas: 3–7 discussion points, each with scope one-liner, designated lead persona (whose expertise it touches most), and a note on where conflict is expected. JSON output. |
| `MOD_POINT_OPEN_PROMPT` | POINT_OPEN | Procedural voice; ≤120 words; frame the stakes; hand to lead by name. Neutrality clause: never state a substantive view. |
| `PERSONA_TURN_PROMPT` (system) | all persona turns | Identity, focus (`weightage` text), facets; the persona's **private briefing block** ("the sponsor has shared the following with you privately — use it in your arguments and cite it where relevant, but do not reveal it was a private briefing"); the behavioral contract: stay in character, ≤250 words, reference specific prior statements when disagreeing, concede explicitly when convinced, always land on a concrete position, address colleagues by name, no meta-commentary about being an AI or the format. Turn-specific instruction appended per state — including the **closing-statement variant**: strongest remaining argument, a direct answer to the Chair's stated unresolved question, and what you would concede; no new topics. |
| `MOD_CONFLICT_CHECK_PROMPT` | CONFLICT_CHECK | JSON-only: stance per non-lead persona given the lead statement. Not spoken; stored in `debug_records`. |
| `MOD_FLOW_DECISION_PROMPT` | REBUTTAL_LOOP | JSON-only: {action: invite_reply\|next_speaker\|to_chair, next_speaker?, reason}. Includes remaining turn budget so the model can economize. |
| `MOD_HANDOFF_PROMPT` | INVITED_RESPONSE / CLOSING_STATEMENTS | 1–2 sentence spoken handoff, naming the invitee and the tension being explored; for closing statements, also states the Chair's key unresolved question on the record. |
| `CHAIR_DECISION_REVIEW_PROMPT` | DECISION_REVIEW | JSON-only over the point's record: {closeness: clear\|close, leaning, key_unresolved_question, divided_parties}. Stored in `debug_records`. |
| `CHAIR_RULING_PROMPT` | POINT_RULING | The **decision contract** (§6.2): commit to one course of action; "it depends"/split-the-difference blends prohibited; name rejected alternatives and why; record dissent as overruled or accommodated; tie-break order = user PriorityUpdates > persona weights > own judgment; still-close ⇒ rule anyway + low-confidence/reversible flag + validation follow-up task. Dual output: spoken ruling (≤300 words) + `PointResolution` JSON. States the decision hierarchy (User > Chair > Personas). |
| `CHAIR_CHALLENGE_PROMPT` | challenge intervention | One turn: revise the ruling (with updated `PointResolution`) or defend it by restating the decisive reasoning — never both, never more than once. A reaffirmed challenge becomes a recorded `sponsor_override`; do not re-argue. |
| `MOD_INTERVENTION_ACK_PROMPT` | intervention drain | Classify intent if untyped; acknowledge; state concrete effect; emit `PriorityUpdate` JSON when it's an override (binding on the Chair). Routes challenges to the Chair. |
| `CHAIR_SYNTHESIS_PROMPT` | SYNTHESIS | From rulings + priority updates + sponsor overrides: overall recommendation, decision log, consolidated/deduplicated action items with owners/priority/timeline, follow-up tasks & open questions. Sponsor overrides reported verbatim, not re-litigated. |
| `WRAP_QA_PROMPT` | WRAP_QA | Route a user question to the Chair or a named persona; answer grounded in the discussion record. |
| `DISCUSSION_TITLE_PROMPT` | after confirm | Reuse `generate_conversation_title()` as-is. |

Formatting contracts that code parses (JSON schemas, the dual spoken+JSON ruling format) live in these prompts — the same edit-in-prompts-not-in-code rule the project already follows for `FINAL RANKING:`.

---

## 10. Failure Handling

| Failure | Behavior |
|---|---|
| Persona model call fails (after 1 retry) | Moderator turn on the record: "<Persona> is unavailable; noting their prior stated position." Point continues. If the *lead* fails on its statement, Moderator offers the user (via a gate-like `state` payload) to retry, reassign the persona's model, or skip the point. |
| Structured Moderator call unparseable | One re-ask with "return only JSON". Then defaults: CONFLICT_CHECK → invite all non-lead personas in weight order (capped by budget); FLOW_DECISION → `to_chair`. |
| `DECISION_REVIEW` unparseable | One re-ask, then treat as `clear` (skip closing statements, go straight to ruling). |
| `PointResolution` JSON missing from ruling | One re-ask, then store the spoken ruling text as `decision`, empty structured fields, flag `"degraded": true`. |
| Chair model call fails (after 1 retry) | Fall back to the Moderator model *for that one ruling only*, flag the resolution `"degraded": true`, and note the substitution on the record. |
| `/turn` while a turn is generating | 409; client treats as "in flight" and re-polls session. |
| Server restart mid-discussion | Session JSON is write-through; rehydrate and continue. A turn that died mid-generation simply never happened (no partial writes). |
| User closes tab | Nothing generates (client-driven turns) — the session naturally freezes and resumes on return. This is a *feature* of the transport choice. |
| Budget exhausted | Forced ruling/synthesis with on-record acknowledgment (§6.4). |
| Attachment not usable (PDF text extraction fails; image attached but persona's model is not multimodal) | Upload succeeds with a warning surfaced in the UI; the briefing block notes "attachment <name> could not be read" so the persona (and user) know it's not in play. Never silently drop content. |
| All models for a point fail | Point marked `skipped` with a transcript note; session continues; surfaced in synthesis follow-ups. |

---

## 11. Build Plan (step-by-step, for an AI implementer)

Each phase is a working increment with acceptance criteria. Do not reorder. Commit per phase.

### Phase 1 — Core orchestrator + state machine (no UI)
- `discussion.py`: session dataclass, state machine (§6.1–6.2) **with the two-agent split (Moderator + Chair as separate prompt contexts and configurable models)**, budgets, transcript, JSON persistence in `data/discussions/`. Text-only persona briefings supported in prompt assembly from day one (attachments come in Phase 5).
- All prompts from §9 in `prompts.py`.
- Config additions (§7.1).
- **Smoke script** `scratch/test_live_discussion.py`: creates a session for a canned problem, auto-confirms suggested personas/agenda, loops `advance()` to completion, prints the transcript with speaker labels (moderator/chair/persona), prints the synthesis. Include a flag to force `DECISION_REVIEW` to return `close` so the closing-statements path is exercised deterministically. (Follow the existing `scratch/test_persona_council.py` style; run with `uv run python scratch/test_live_discussion.py`.)
- ✅ *Accept:* smoke script produces a coherent multi-point discussion where personas reference each other's arguments; every point ends with a parseable `PointResolution` that **names a decision and at least one rejected alternative** (no split-the-difference outputs in spot checks); the forced close-call run shows closing statements from the divided parties followed by a ruling flagged low-confidence/reversible with a validation follow-up; session JSON on disk fully describes the run; budgets demonstrably cap a point (test with budget=2).

### Phase 2 — HTTP API
- All endpoints from §7.2 in `main.py`, including the per-turn SSE response (whole-turn events; no token deltas yet), gates returning state-only, the 409 in-flight guard, and intervention queueing (including `target_point` for challenges).
- ✅ *Accept:* the full flow is drivable with `curl`/httpie alone: create → suggest/confirm personas → suggest/confirm agenda → repeated `/turn` → completed session with synthesis; an `/intervene` POST between turns visibly changes the next turn; refreshing via `GET` mid-discussion returns consistent state.

### Phase 3 — Frontend: watchable step-mode discussion
- New discussion flow in the frontend: creation screen (Step 1), persona review reusing existing persona-card UI (Step 2), agenda review (Step 3), transcript view with moderator/chair/persona styling — Chair rulings as decision cards — and agenda rail (Step 4, **step mode only**: a "Next turn" button), synthesis panel (Step 5). Sidebar lists discussions.
- ✅ *Accept:* a user can run an entire discussion from the browser clicking "Next turn", with correct attribution, colors, agenda progress, decision cards on each ruling, and a rendered decision panel at the end.

### Phase 4 — Interventions + pacing
- Intervention composer with type chips wired to `/intervene`; all nine behaviors from §4.2 including **challenge decision** and text-only **brief persona** (Step-2 briefing text field also lands here). Auto-advance loop with configurable gap, Pause/Resume, mode toggle.
- ✅ *Accept:* during auto-advance, submitting a priority override results (within one turn) in a Moderator acknowledgment that names the override, and subsequent Chair rulings reflect it; challenging a ruling produces exactly one revise-or-defend Chair turn, and reaffirming records a sponsor override on the resolution; a text briefing to one persona shows up as a delivery stub in the transcript and demonstrably informs that persona's next turn (and no other persona's); skip and end-discussion work; pause halts generation within one turn.

### Phase 5 — Wrap-up Q&A, export, attachments, resilience polish
- WRAP_QA state + UI; markdown export of transcript + decision package (including sponsor overrides); **briefing attachments**: the multipart upload endpoint, PDF/txt/md text extraction, image pass-through for multimodal persona models, briefing indicators in the cast strip; failure-handling paths from §10 exercised (kill a model id to test degradation, including the Chair-model fallback and an unreadable attachment); title generation; delete.
- ✅ *Accept:* export produces a self-contained markdown decision document; a persona with an invalid model id degrades per §10 without ending the session; an invalid Chair model id falls back to the Moderator model for the ruling and flags it degraded; a PDF briefed to one persona is cited by that persona in discussion; an image briefed to a non-multimodal persona surfaces a visible warning rather than silently vanishing.

### Phase 6 — Nice-to-haves (only after 1–5)
- Token-level streaming of the active turn (SSE deltas). Chair and Moderator models selectable in UI (also closes the `ideas-scratchpad.md` chairman-selectable item). Per-session budget editor. UI toggle to inspect `debug_records` (conflict checks, decision reviews). "Re-open point" beyond the single challenge exchange. Conflict-heat indicator on the agenda rail.

---

## 12. Cost & Latency Expectations (set user expectations in UI)

Rough per-session call count with defaults (5 points, ~6 persona turns/point average):
- Setup: ~3 calls (personas, agenda, title)
- Per point: 1 open + 1 lead + 1 conflict-check + ~4 invited/rebuttal + ~3 flow-decisions + 1 decision-review + 0–2 closing statements + 1 ruling ≈ 12–14 → ~65 for 5 points
- Synthesis + acks/challenges: ~6
- **Total ≈ 70–80 calls**, most of them short and most on the cheap Moderator model — cost is dominated by persona turns and Chair rulings. This exceeds a Persona-mode run (~10 calls) several-fold; the turn-budget indicator and the session hard cap exist precisely for this, and the UI should show a running call count.

Latency per turn ≈ one model call (2–15s). Auto-advance therefore feels like a real chat with people typing — that's desirable, not a bug to optimize away.

---

## 13. Open Questions (decide before/while building; defaults given)

1. **Should personas see each persona's numeric weight?** Default **no** — weights inform only the Chair's rulings (mirrors existing Stage 3 design; prevents personas from deferring pre-emptively).
2. **Structured-call visibility (conflict checks, decision reviews).** Default: not in the transcript, but stored in `debug_records` and inspectable — consistent with the project's "all raw outputs inspectable" transparency principle. UI toggle is a Phase 6 item.
3. **Re-opening resolved points beyond the single challenge exchange.** Default v1: the one revise-or-defend challenge turn, plus wrap-up Q&A; full re-litigation is a Phase 6 candidate (budget protection).
4. **Discussions and conversations in one sidebar list or two sections?** Default: one list, type-badged.
5. **Minimum viable persona count.** Default 3 (a 2-persona "discussion" is a debate; still allow it, but the suggestion prompt targets 3–5).
6. **Should the Chair's `leaning` from DECISION_REVIEW ever be shown to personas before closing statements?** Default **no** — only the *key unresolved question* is stated on the record. Revealing the leaning would invite sycophantic convergence toward it instead of genuine final arguments.
7. **Should the Chair (or other personas) see a persona's briefing contents?** Default **no** — briefings are private to the briefed persona; facts from them enter the record only through that persona's spoken arguments, exactly like an expert's private knowledge in a real meeting. The transcript's delivery stub keeps the *existence* of the briefing on the record. Revisit if users find rulings ignore un-voiced briefing facts (the fix would be a user choice per briefing: private vs. on the record).

---

## 14. Success Criteria (product-level)

1. A non-technical user can go from problem → confirmed cast → confirmed agenda → watched discussion → decision package without reading docs.
2. In ≥80% of sessions on real prompts, at least one persona *changes or concedes a position* in response to another's argument — the debate is real, not parallel monologues (spot-check qualitatively).
3. **Rulings are decisive:** in spot checks, every `PointResolution` commits to a single course of action and names at least one rejected alternative; zero split-the-difference non-decisions.
4. A user intervention mid-discussion is acknowledged within one turn and demonstrably alters at least the current point's ruling; a challenged ruling gets exactly one revise-or-defend response, and a reaffirmed challenge is recorded as a sponsor override.
5. Every completed session yields ≥1 action item with an owner and a per-point decision log.
6. No session exceeds its hard call cap; no single model failure ends a session.
