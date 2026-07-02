# PRD: Live Council Discussion (Interactive Persona Deliberation)

**Status:** Draft v7
**Author:** Nishant (concept) / drafted with Claude
**Date:** 2026-07-02
**v7 changes:** Added **post-session amendments** (§4.6) — sponsor authority doesn't expire at `COMPLETED`. The user can override decisions, edit/close action items, and annotate follow-ups after the session ends. Amendments are **append-only**: the original ruling is always preserved and shown as overridden, never erased. Amended decisions are what future precedent-linked sessions inherit; an optional Chair call regenerates the report/brief marked "Amended".
**v6 changes:** Added **precedent sessions** (§4.5) — at creation, the user can link one or more previous *completed* discussions; their final decisions are snapshotted into the new session as a **"line in the sand"**: all personas and both agents see them as standing decisions, binding by default (per-decision user override to "open for revisit"), the agenda can't re-open them, agenda-challenge proposals contradicting them are rejected with the precedent cited, and Chair rulings must stay consistent with them. Personas can flag a structured `precedent_conflict` once; only the user can release a precedent.
**v5 changes:** Agenda drafting moves from the Moderator to the **Chair** (agenda-setting is a substantive framing decision; a **reasoning/thinking model** is now the recommended default for the Chair). Added an **agenda challenge round** (§6.2): before the user gate, each persona receives the draft agenda and gets exactly **one chance** — announced as such — to argue succinctly for an addition; the Chair rules admit/fold/reject on each argument with reasons on the record. The user still holds the final gate and can re-add anything rejected.
**v4 changes:** Added §13 — an optional, per-session **persona airtime budget** mechanic (scarcity forces personas to spend words only on points they're genuinely convinced about) plus an **A/B experiment framework** (paired-run harness, automatic metrics, blind LLM judge, in-product variant tagging) to test budget vs. no-budget before deciding whether it becomes a default.
**v3 changes:** Added an **impact round** — after the last ruling, each persona receives the final decision log (dissent dispositions included) and reports the impact on its domain (additional work, steps, considerations, dependencies). The closing output is now **two documents**: a **full report** (all discussions, decisions, rationale, important dissent, way forward) and a **concise decision brief** (decisions plus unresolved items and close/reversible calls with their dependencies).
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
- Once decisions are made, they go **back around the table**: each function states what the decision means for them — extra work, new steps, risks — even the ones who were overruled (disagree and commit).
- The meeting ends with **decisions, action items, and owners** — not an essay — and the minutes come in two forms: the full record for those who need it, and a one-page decision brief for everyone else.
- Anyone in the room (especially the sponsor) can **interject at any time** with new context, an opinion, or a priority override — and can challenge a decision they think is wrong.

**Live Council Discussion replicates this.** The user poses a problem, confirms the cast of expert personas and their focus areas, approves the agenda, and then watches a live chat where personas debate each agenda point under the Moderator's facilitation — with every point closed by an explicit, on-the-record decision from the Chair, and the user able to intervene at any turn. The output is a decision document: per-point rulings, an overall recommendation, action items, and follow-up tasks.

---

## 2. Goals & Non-Goals

### Goals

1. **Transparency of deliberation.** The user sees *how* the answer was reached — every argument, rebuttal, concession, and ruling, in order, attributed to a named persona or agent.
2. **Genuine dialectic.** Personas respond to each other's actual words (not blind parallel answers). Conflict is surfaced deliberately, argued, and then *decided* — not summarized away.
3. **Accountable decisions.** Every agenda point ends with one committed course of action from the Chair, with rejected alternatives named and dissent recorded. No "both sides have merit" non-decisions.
4. **User participation at any point.** The user can pause, inject context, state their own perspective, override priorities, redirect, skip, challenge a decision, or end early — and the discussion visibly incorporates it. The user can also **brief any individual persona privately** with additional context (text or attached documents), at setup or mid-discussion, the way a sponsor hands an expert the relevant report before a meeting.
5. **Decisions ripple back to the room.** After the last ruling, every persona receives the final decision log (dissent noted) and reports the concrete impact on its domain — additional work, steps, considerations, dependencies on other functions — including personas that were overruled (disagree and commit). These impact statements feed the action items.
6. **Structured, actionable, two-tier output.** Every session ends with (a) a **full report** — all discussions summarized, each decision with its rationale, important dissent, and the way forward — and (b) a **concise decision brief** — the decisions in one line each, plus unresolved items and close/reversible calls with their dependencies. Action items and follow-up tasks carry suggested owners.
7. **Bounded cost and time.** The discussion protocol has explicit turn budgets so a session can't spiral into unbounded token spend.
8. **Confirmation gates.** Nothing expensive runs until the user has confirmed the problem framing, the personas, and the agenda.

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

6. **The decision hierarchy is User > Chair > Personas, and user interventions always win.** Personas advise and never vote; the Chair holds delegated decision authority and is accountable for every ruling; the user is the sponsor and holds final authority. An intervention enters the transcript like any other utterance and is processed at the next turn boundary — before any queued turn. A priority override from the user is binding: the Moderator acknowledges it, and every subsequent Chair ruling must reflect it. Rulings are never beyond the sponsor's reach — during the session the user can challenge any decision (§4.2), and **after** the session the user can amend any decision, action item, or follow-up (§4.6). Amendments are append-only: the original ruling stays on the record, marked overridden — the sponsor can overrule the council, but nobody, including the sponsor, silently rewrites history.

7. **Conflict is invited, not defaulted.** After a lead persona presents, the Moderator explicitly determines *which* other personas materially disagree or have something to add (via a cheap structured "conflict check" call), and invites only those. "Everyone speaks on everything" recreates the batch mode's redundancy and burns the turn budget.

8. **Close calls get final arguments, then a ruling — never a blend.** Before ruling, the Chair reviews the point's record (structured call). If the decision is genuinely close, it names its key unresolved question and the divided parties each give one closing statement — at most once per point — before the Chair rules. If it's *still* close, the Chair decides anyway, flags the ruling low-confidence/reversible, and generates a validation follow-up task. Splitting the difference to avoid deciding is a prohibited output.

9. **Everything is budgeted.** Per-point and per-session turn caps (§6.6) are hard limits enforced by the orchestrator, not suggestions in a prompt. When a budget is hit, the Chair is forced to rule on what's on the record ("in the interest of time…").

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
Step 3  AGENDA     Chair (reasoning model) drafts the discussion agenda: 3–7 bullet points,
                   each with a one-line scope and a designated lead persona.
                     → AGENDA CHALLENGE ROUND: each persona receives the draft and gets
                       exactly ONE chance — told so up front — to argue for an addition
                       (succinct, strong: what's missing, why it can't fold into an existing
                       point, ≤150 words) or to pass on the record. The Chair then rules on
                       every argument in one turn: admit (new point, with lead), fold (expand
                       an existing point's scope), or reject — each with a one-line reason.
                     → user reviews the final agenda WITH the challenge log (admitted and
                       rejected proposals visible), edits/reorders/deletes/adds — including
                       re-adding anything the Chair rejected (sponsor override) → confirms.
                                                                                   [GATE]
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
Step 5  IMPACT     After the last point is ruled (or the user ends the discussion), the
                   Moderator circulates the final decision log — every ruling with its
                   dissent dispositions and any sponsor overrides — and each persona gives
                   one impact statement: additional work in its domain, concrete steps,
                   considerations/risks, and dependencies on other functions. Overruled
                   personas respond in disagree-and-commit mode. User can skip this round.
Step 6  SYNTHESIZE Chair produces two documents:
                     • FULL REPORT — problem, per-point discussion summaries, each decision
                       with its rationale, important dissent, impact summaries, action items
                       (owner, priority, suggested timeline), follow-ups, sponsor overrides,
                       and the way forward.
                     • DECISION BRIEF — one page: each decision in a line or two, plus
                       unresolved items, close/reversible calls with their validation tasks,
                       and cross-functional dependencies surfaced in the impact round.
Step 7  WRAP       User can ask follow-up questions to the Chair or any persona (bounded
                   Q&A turns), then the session is archived like any conversation.
```

### 4.2 User intervention (the core differentiator)

An intervention composer (text box + type selector) is **always visible** during Step 4. Interventions take effect at the next turn boundary — the currently rendering turn finishes, then the user's message enters the transcript and must be addressed in the next turn.

| Intervention type | Example | Required behavior |
|---|---|---|
| **Add context** | "FYI: we already have a signed contract with vendor X until 2027." | Moderator acknowledges; restates how it changes the current point; personas see it in transcript from now on. |
| **Own perspective** | "As the founder, I think speed matters more than polish here." | Moderator acknowledges; the Chair treats it as a strongly-weighted voice in this and future rulings. |
| **Priority override** | "Deprioritize cost — budget is not the constraint. Security is." / "Release the vendor-X precedent — that decision is back on the table." | Binding. Moderator restates revised priorities and may re-order remaining agenda; every subsequent Chair ruling must reflect the override. Also the mechanism for **releasing a precedent decision** (§4.5) — the released decision is marked revisitable on the record. |
| **Direct question** | "@Security Architect — does this hold if we're SOC2 audited?" | Moderator gives the floor to that persona for one answer turn, then resumes. |
| **Brief persona** | (to Security Architect) "Here's our latest pen-test report — attached." | Content (text + attachments) is added to that persona's **private briefing** and informs all its future turns. The transcript records that a briefing was delivered (not its contents). No LLM turn is consumed. |
| **Challenge decision** | "That ruling is wrong — we are not dropping vendor X." | The Chair gets one turn to either **revise** the ruling or **defend** it (restating the decisive reasoning). If the user reaffirms the challenge, the user's position stands and is recorded on the resolution as a **sponsor override** — the Chair does not argue further. |
| **Redirect / skip** | "We've covered this. Move to the next point." | Chair immediately rules on the current point with what's on record; Moderator advances. |
| **Pause / resume** | (button) | No new turns are generated until resume. Step mode (§4.3) is the generalization. |
| **End discussion** | "Wrap it up." | Chair rules briefly on the current point, then the session proceeds to the impact round and synthesis (Steps 5–6). The user is offered a skip of the impact round ("Finalize now"). |

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
- **Cast strip (top).** Moderator and Chair identity chips (with their models), then persona chips with name, model, weight, a briefing indicator (📎 count) when the persona has been briefed, and a remaining-airtime meter when the airtime economy is enabled (§13); hover for focus area. During Step 2 this is the editable persona card UI (reuse the existing persona-mode cards, including model dropdown grouped by cost tier and weight validation) **plus a per-persona briefing section: free-text field and file attach (PDF/txt/md/images)**. Clicking a persona chip mid-discussion opens its briefing for additions.
- **Decision panel (Steps 5–6).** Two tabs: **Brief** (default — the one-page decision brief: decisions, unresolved items, close/reversible calls, dependencies) and **Full report** (per-point discussion summaries, rationale, dissent, impact statements, action items table, follow-ups, sponsor overrides). Each tab exportable as markdown separately. Impact statements also appear inline in the transcript as regular persona turns during Step 5.

### 4.5 Chaining sessions: precedent decisions ("line in the sand")

At creation (Step 1), the user may link one or more previous **completed** discussions as **precedent sessions**. Organizations don't decide in a vacuum — this makes a new discussion start from what was already decided, instead of re-litigating it.

- **What's carried.** A **snapshot**, copied into the new session at creation (so later deletion or edits of the old session can't corrupt it): each precedent's per-point decision log (decision + one-line rationale + dissent dispositions + sponsor overrides, **as amended at that moment** — post-session amendments (§4.6) are the organization's current decisions), its decision brief, and its unresolved items / validation follow-up tasks.
- **Per-decision status.** Every carried decision defaults to **binding**. In the creation UI the user can flip individual decisions to **open for revisit**. Decisions the old session flagged low-confidence/reversible are visually highlighted as natural candidates to open — a validation session is often exactly why you chain.
- **Effect on the room.** All personas and both agents see a **Standing Decisions** block in the fixed prompt header (§7.3). Personas must not re-litigate a binding precedent — they argue *within* it, and their positions must be compatible with it. A persona that believes the current problem genuinely invalidates a precedent may flag a one-line structured `precedent_conflict` (once per persona per precedent); the Chair notes it on the record and routes it to the user — **only the user can release a precedent**, mid-discussion via a priority-override intervention naming it (binding on the Chair like any override).
- **Effect on the agenda.** The Chair's draft must not schedule points that re-open binding precedents, and should pick up the precedents' unresolved items and validation follow-ups as candidate points. Agenda-challenge proposals that contradict a binding precedent are rejected with the precedent cited (unless the user opened it).
- **Effect on rulings and output.** Chair rulings must be consistent with binding precedents and cite them whenever they constrain the outcome. The new session's report and brief list the precedents relied on, and any unreleased `precedent_conflict` flags appear under "unresolved" in the brief.
- **UI.** Step 1 gains a "Build on previous session(s)" picker (completed discussions only, with brief preview and per-decision binding/open toggles). During discussion, a pinned **Standing Decisions** card sits on the agenda rail; decisions released by the user mid-session get a visible "released" badge.

### 4.6 Post-session amendments (sponsor authority doesn't expire)

A `COMPLETED` session's record stays open to its sponsor. From the decision panel of any completed session, the user can:

- **Override a decision.** Each decision card gets an "Override" action: the user supplies the new decision and (optionally) a reason. The card then shows the original Chair ruling struck through/collapsed with a **Sponsor-amended** badge and timestamp — the original is preserved, never deleted.
- **Edit, close, or reassign action items** and annotate or resolve follow-ups. Same append-only treatment: prior values kept in the amendment record.
- **Regenerate the documents (optional).** One Chair call re-issues the report and brief incorporating all amendments, clearly marked "Amended <date>"; the prior versions are kept in a history list. Without regeneration, the UI and exports simply overlay amendments on the original documents (original text + amendment side by side).

Rules:

- Amendments never reopen the session, generate persona turns, or invite counter-argument — the discussion is over; this is the sponsor exercising final authority over the outcome (Principle 6). If the user wants the council's reaction to a changed decision, that's a **new session chained to this one** (§4.5) with the amended decision in the precedent snapshot.
- **Precedent interaction:** precedent snapshots taken at creation always carry the decisions *as amended at that moment* (the amended decision is the organization's decision). Sessions that linked this precedent *before* the amendment keep their old snapshot — by design (§4.5); the UI shows a notice on such sessions ("a precedent was amended after linking") so the user can decide whether that matters.
- Amendments are timestamped, attributed to the user, and exported with the record.

---

## 5. Roles

| Role | Played by | Responsibilities |
|---|---|---|
| **Moderator** (facilitator) | `DISCUSSION_MODERATOR_MODEL` — default `google/gemini-2.5-flash` (cheap + fast; also runs all structured flow calls) | Propose personas; open points; pick lead + invited speakers via structured decisions; enforce budgets; acknowledge, classify, and route interventions; convene closing statements and the agenda challenge round. **Strictly neutral — never expresses a substantive opinion and never decides anything substantive.** |
| **Chair** (adjudicator) | `DISCUSSION_CHAIR_MODEL` — selectable per session in the UI; **a reasoning/thinking model is the recommended default** (agenda framing and adjudication are the two places deliberate multi-step reasoning pays for itself) | **Drafts the agenda** and rules on agenda challenges (admit/fold/reject, with reasons). Speaks only at decision moments. Reviews each point's record; calls for closing statements when the decision is close; then **rules**: one committed course of action, rejected alternatives named with reasons, dissent recorded as overruled or accommodated, confidence and reversibility flagged. Responds to decision challenges (revise or defend once). Produces the two closing documents: the full report and the decision brief. Accountable for every ruling; overrideable only by the user. |
| **Persona** (3–5) | Its user-assigned model from `PERSONA_MODEL_CHOICES` | Argue its point of view from its focus area (`weightage` text); present when lead; rebut only when invited; give a closing statement when convened; concede when convinced; deliver an **impact statement** on the final decisions (additional work, steps, considerations, dependencies — in disagree-and-commit mode if overruled); stay in character; keep turns short (§9). **Advisors only — personas never vote.** Numeric `weight` is an input to the Chair's judgment, not a ballot. |
| **User** | Human | Sponsor of the decision and **final authority**: confirms gates, intervenes, sets binding priorities, can challenge and override any ruling, ultimately owns the outcome. |

**Decision hierarchy: User (sponsor) > Chair (delegated decider) > Personas (advisors).** This ordering is stated in the Chair's and Moderator's prompts and enforced by the intervention rules in §4.2/§6.5.

---

## 6. Discussion Protocol (state machine)

### 6.1 Session states

```
CREATED → FRAMING → PERSONA_PROPOSAL → PERSONA_REVIEW ⟲ → AGENDA_PROPOSAL → AGENDA_CHALLENGE
        → AGENDA_REVIEW ⟲ → DISCUSSION → IMPACT_ROUND → SYNTHESIS → WRAP_QA ⟲ → COMPLETED
   (any state) → ABORTED          (IMPACT_ROUND skippable by user control)
```

- `PERSONA_REVIEW` and `AGENDA_REVIEW` loop on user edits ("re-suggest with this feedback" re-invokes the proposal call with the user's notes appended) until an explicit confirm. A re-suggested agenda does **not** re-run `AGENDA_CHALLENGE` — one challenge round per session.
- `AGENDA_CHALLENGE` is described in 6.2; it runs turn-by-turn (via `/turn`, like the discussion) between the Chair's draft and the user gate.
- `DISCUSSION` contains a nested per-point machine (6.3), iterated over `agenda[]` in confirmed order.
- `IMPACT_ROUND` is described in 6.4; `SYNTHESIS` produces the two closing documents (full report, then decision brief — two separate Chair calls, the brief distilled from the report + resolutions).

### 6.2 Agenda challenge round (before the user gate)

```
CHALLENGE_OPEN        Moderator: 1 turn. Circulates the Chair's draft agenda on the record and
                      states the rule explicitly: each persona has EXACTLY ONE opportunity to
                      propose an addition — there is no second round, so make it succinct and
                      strong, or pass.
CHALLENGE_STATEMENT   One turn per persona (weight desc order). Either a recorded pass, or ONE
                      proposed addition, ≤150 words, structured as: the missing point (title +
                      one-line scope) · why it materially affects the decision · why it cannot
                      be folded into an existing agenda point · suggested lead persona.
                      Proposing more than one addition forfeits all but the first.
AGENDA_RULING         Chair: 1 turn + structured record. Rules on every proposal in one pass:
                        • admit — new agenda point (with lead and position in the order),
                        • fold  — an existing point's scope is expanded to absorb it, or
                        • reject — with a one-line reason on the record.
                      Ruling quality bar: judge the ARGUMENT (material impact on the decision),
                      not the seniority/weight of the proposer. JSON: updated agenda[] +
                      per-proposal {persona_id, ruling, reason}.
```

The one-shot rule is the point: scarcity of opportunity forces personas to lead with their strongest case (the same conviction mechanism §13 generalizes with airtime). The round costs no airtime (§13.1) — it precedes the wallets. The user gate that follows shows the full challenge log; rejected proposals can be re-added by the user as a sponsor override.

### 6.3 Per-point states

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

### 6.4 Impact round (after the last ruling)

```
IMPACT_OPEN           Moderator: 1 turn. Announces that decisions are final and circulates
                      the decision log on the record: every ruling with its dissent
                      dispositions and any sponsor overrides.
IMPACT_STATEMENT      One turn per persona (agenda-relevance order, ties by weight desc).
                      Each persona responds to the FULL decision log from its domain's
                      perspective, structured as: Additional work · Concrete steps ·
                      Considerations/risks · Dependencies on other functions · Anything else
                      relevant. Overruled personas respond in disagree-and-commit mode: the
                      decision is not re-argued; they state what executing it takes and what
                      to watch for. No rebuttals, no cross-talk — this round is reporting,
                      not debate.
```

Impact statements are ordinary transcript turns (type `impact_statement`) and are a primary input to synthesis: the Chair consolidates their work items into the action-items table and their cross-functional dependencies into the decision brief. If an impact statement surfaces something that *genuinely invalidates* a ruling, the persona may flag it as a `blocking_concern` (one line, structured) — the Chair does not reopen the point automatically, but the concern is listed under "unresolved" in the brief and offered to the user as a challenge candidate.

### 6.5 Intervention handling (uniform rule)

At every turn boundary the orchestrator drains the intervention queue **before** generating the next planned turn:

1. Append the user's message(s) to the transcript.
2. Generate one Moderator `INTERVENTION_ACK` turn that (a) classifies/acknowledges the intervention, (b) states its effect (per the table in §4.2), and (c) for overrides, emits a structured `PriorityUpdate` record stored on the session (binding on all subsequent Chair rulings).
3. Resume the per-point machine — possibly in a modified position:
   - `skip` jumps to `POINT_RULING`;
   - `end` forces a brief `POINT_RULING` then jumps to `IMPACT_ROUND` (with a "Finalize now"
     option to skip straight to `SYNTHESIS`);
   - a direct question inserts one `INVITED_RESPONSE` for the named persona;
   - `brief_persona` appends to the target persona's `briefing` and writes a delivery-stub
     transcript entry ("User briefed <persona>") — no LLM call, no Moderator ack turn;
   - **`challenge`** (targets a resolved point) inserts one Chair turn: revise the ruling (updating its `PointResolution`) or defend it once. A reaffirmed challenge writes a `sponsor_override` onto the resolution and the discussion moves on — the Chair does not re-argue.

### 6.6 Budgets (defaults, all configurable per session)

| Budget | Default |
|---|---|
| Agenda points | 3–7 (Chair proposes; user gate controls final count) |
| Agenda challenge round | 1 proposal per persona, ≤150 words, once per session; 1 batch Chair ruling |
| Turns per point (persona turns, excl. procedure) | 8 |
| Reply chain depth per exchange | 2 (statement → rebuttal → reply, then Moderator moves on) |
| Closing-statement rounds per point | 1 round max; max 2 personas, 1 turn each |
| Challenge exchanges per resolved point | 1 (revise-or-defend, then sponsor override applies) |
| Impact round | 1 turn per persona, ≤ 250 words; no rebuttals |
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

**`backend/openrouter.py`** unchanged, except: add optional `max_tokens` param to `query_model()` (turn-length ceilings) if not already supported, and optional passthrough of OpenRouter's `reasoning` parameter (effort/max reasoning tokens) so a thinking-model Chair can be tuned — high effort for agenda drafting and rulings, low/none for structured JSON calls where latency matters.

**`backend/config.py`**: add `DISCUSSION_DEFAULTS` (budgets from §6.6), `DISCUSSION_MODERATOR_MODEL` (default `google/gemini-2.5-flash`), `DISCUSSION_CHAIR_MODEL` — **default a reasoning/thinking model** (e.g. a `:thinking`-variant or reasoning-capable OpenRouter id; falls back to `CHAIRMAN_MODEL` if unset), since agenda framing and adjudication benefit most from deliberate reasoning. Both agent models are per-session overridable; the same model id in both slots is allowed — the separation is in the prompts and call structure, not the weights.

Standard/Persona code paths: **zero behavioral changes.**

### 7.2 Transport: client-driven turns over plain HTTP + SSE per turn

SSE is server→client only, and this feature is fundamentally interactive — so the design inverts control: **the client requests each turn**, and the server streams that single turn back over SSE. This gives step mode for free, makes auto-advance a trivial client loop, makes pause = "stop requesting", and means interventions are ordinary POSTs with no queue-race against a long-lived stream. It also keeps requests short (no 10-minute SSE connections through nginx) and makes every turn independently retryable.

```
POST   /api/discussions                          → create session {problem, context,
                                                   precedent_session_ids?: [],
                                                   open_decisions?: {session_id: [point_ids]}}.
                                                   Snapshots each precedent's decision log + brief
                                                   into the new session; 400 if any id is not a
                                                   COMPLETED discussion → session JSON
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
POST   /api/discussions/{id}/agenda/suggest      → Chair agenda proposal (reasoning model; accepts
                                                   feedback for re-suggestion). First call moves the
                                                   session into AGENDA_CHALLENGE — the client then
                                                   drives the challenge round with /turn until the
                                                   AGENDA_REVIEW gate is reached (re-suggestions
                                                   don't repeat the challenge round).
POST   /api/discussions/{id}/agenda/confirm      → body: final agenda[] (ordered points, lead per
                                                   point — may include user re-adds of rejected
                                                   challenge proposals)
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
POST   /api/discussions/{id}/control             → body: {action: skip_point|end_discussion|
                                                   skip_impact_round|abort}
POST   /api/discussions/{id}/amend               → only when COMPLETED (409 otherwise — during a
                                                   session, use the challenge intervention). Body:
                                                   {target: {kind: decision|action_item|follow_up,
                                                   id}, new_value, reason?}. Appends to
                                                   amendments[]; never mutates the original record.
POST   /api/discussions/{id}/regenerate-docs     → optional; one Chair call re-issuing report +
                                                   brief with amendments applied, marked "Amended";
                                                   prior versions pushed to synthesis.history
GET    /api/discussions/{id}                     → full session (rehydration/refresh)
GET    /api/discussions                          → list summaries
DELETE /api/discussions/{id}                     → delete
```

Auto-advance: client calls `/turn`, waits `gap_ms` after `turn_complete`, calls again — stopping on pause, gate, or `COMPLETED`. Token-level streaming of the active turn is a should-have (start with whole-turn `turn_complete` events; the SSE shape above already accommodates deltas later).

### 7.3 Context-window strategy

Transcripts grow. Prompts are assembled per-turn from:

1. **Fixed header:** problem statement, user context, **Standing Decisions block** (precedent snapshots with binding/open/released status, when the session has precedents — §4.5), confirmed personas roster (names + focus one-liners + weights, weights visible to Moderator/Chair only — see §14), agenda, current `PriorityUpdate`s. For persona turns only: that persona's own private briefing (extracted text inline; image attachments passed as model inputs when the persona's model is multimodal).
2. **Resolved-point summaries:** for each completed point, only its `PointResolution` JSON rendered as 3–4 lines — not the full exchange.
3. **Current point verbatim:** the full transcript of the point under discussion.
4. **Recent interventions verbatim** (they're short and load-bearing).

This keeps per-turn prompt size roughly O(current point + summaries), not O(entire session). Impact-round turns get the full decision log (all `PointResolution`s rendered) instead of a current point. The full-report synthesis call gets all `PointResolution`s, the impact statements verbatim, and the decision-relevant interventions/sponsor overrides — not the raw debate transcript. The brief call gets the finished report plus the resolutions and distills; it introduces no new content.

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
              "budgets": { /* §6.6 */ }, "gap_ms": 2000 },
  "precedents": [                            // snapshot taken at creation — never a live reference
    { "session_id": "uuid", "title": "…", "brief": "markdown snapshot",
      "decisions": [ { "point_id": "a2", "point_title": "…", "decision": "…",
                       "rationale_one_line": "…", "was_reversible": false,
                       "status": "binding|open|released",
                       "released_turn_id": null } ],
      "unresolved": ["…"] }
  ],
  "personas": [
    { "id": "p1", "name": "Security Architect", "weightage": "focus text…",
      "facets": ["…"], "model": "openrouter/id", "weight": 0.4, "color": "#…",
      "briefing": {
        "text": "user-provided private context | ''",
        "attachments": [ { "id": "f1", "filename": "pentest-2026.pdf", "mime": "application/pdf",
                           "extracted_text": "…|null" } ]   // files on disk under
      } }                                                    // data/discussions/{id}/attachments/
  ],
  "agenda_challenges": [                     // one entry per persona, from the challenge round
    { "persona_id": "p2", "turn_id": 9, "passed": false,
      "proposal": { "title": "…", "scope": "…", "suggested_lead": "p2" },
      "argument": "≤150-word case",
      "ruling": "admitted|folded|rejected", "folded_into": "a3|null", "reason": "one line" }
  ],
  "agenda": [
    { "id": "a1", "order": 1, "title": "string", "scope": "one-liner",
      "origin": "chair|persona_challenge|user",
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
      "type": "challenge_open|agenda_challenge|agenda_ruling|point_open|lead_statement|invited_response|rebuttal|handoff|closing_statement|ruling|challenge_response|intervention|intervention_ack|briefing_delivered|impact_open|impact_statement|synthesis|qa",
      "content": "markdown",
      "meta": { "model": "openrouter/id", "intervention_type": "override|context|challenge|…",
                "invited_reason": "…",
                "precedent_conflict": { "session_id": "…", "point_id": "…", "reason": "one line" } } }
  ],
  "priority_updates": [ { "turn_id": 21, "summary": "Security > cost", "detail": "…" } ],
  "pending_interventions": [ /* drained at next /turn */ ],
  "action_items": [
    { "id": "t1", "point_id": "a1", "description": "…", "owner_persona_id": "p3",
      "owner_hint": "e.g. 'Eng lead'", "priority": "P1", "timeline": "2 weeks" }
  ],
  "impact_statements": [                     // structured extract alongside the transcript turns
    { "persona_id": "p2", "turn_id": 58, "additional_work": ["…"], "steps": ["…"],
      "considerations": ["…"], "dependencies": ["…"], "blocking_concern": "…|null" }
  ],
  "synthesis": {
    "report": "markdown — full record: discussions, decisions, rationale, dissent, impacts, way forward",
    "brief":  "markdown — one page: decisions; unresolved items; close/reversible calls + validation tasks; cross-functional dependencies",
    "sponsor_overrides": [ /* derived */ ], "follow_ups": ["…"],
    "amended_at": "iso8601|null",
    "history": [ { "ts": "…", "report": "…", "brief": "…" } ]   // pre-regeneration versions
  } | null,
  "amendments": [                            // post-session sponsor edits — append-only (§4.6)
    { "id": "am1", "ts": "iso8601",
      "target": { "kind": "decision|action_item|follow_up", "id": "a2|t1|f0" },
      "original_snapshot": { /* value at time of amendment */ },
      "new_value": "…", "reason": "…|null" }
  ],
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
| `AGENDA_PROMPT` | agenda/suggest (**Chair**, reasoning model) | Given problem + confirmed personas: 3–7 discussion points, each with scope one-liner, designated lead persona (whose expertise it touches most), and a note on where conflict is expected. JSON output. |
| `MOD_CHALLENGE_OPEN_PROMPT` | CHALLENGE_OPEN | Circulates the draft agenda; states the one-shot rule explicitly ("you will not get a second opportunity — argue succinctly and strongly, or pass"). Neutral, procedural. |
| `PERSONA_AGENDA_CHALLENGE_PROMPT` | CHALLENGE_STATEMENT | One recorded pass OR one addition, ≤150 words: missing point (title + scope) · why it materially affects the decision · why it can't fold into an existing point · suggested lead. The one-shot framing is restated in the persona's own instruction. |
| `CHAIR_AGENDA_RULING_PROMPT` | AGENDA_RULING | Rule on every proposal in one turn: admit / fold (naming the absorbing point) / reject, one-line reason each; judge the argument's material impact on the decision, not the proposer's weight. Dual output: spoken ruling + JSON {updated agenda[], per-proposal rulings}. |
| `MOD_POINT_OPEN_PROMPT` | POINT_OPEN | Procedural voice; ≤120 words; frame the stakes; hand to lead by name. Neutrality clause: never state a substantive view. |
| `PERSONA_TURN_PROMPT` (system) | all persona turns | Identity, focus (`weightage` text), facets; the persona's **private briefing block** ("the sponsor has shared the following with you privately — use it in your arguments and cite it where relevant, but do not reveal it was a private briefing"); the behavioral contract: stay in character, ≤250 words, reference specific prior statements when disagreeing, concede explicitly when convinced, always land on a concrete position, address colleagues by name, no meta-commentary about being an AI or the format. Turn-specific instruction appended per state — including the **closing-statement variant**: strongest remaining argument, a direct answer to the Chair's stated unresolved question, and what you would concede; no new topics. |
| `MOD_CONFLICT_CHECK_PROMPT` | CONFLICT_CHECK | JSON-only: stance per non-lead persona given the lead statement. Not spoken; stored in `debug_records`. |
| `MOD_FLOW_DECISION_PROMPT` | REBUTTAL_LOOP | JSON-only: {action: invite_reply\|next_speaker\|to_chair, next_speaker?, reason}. Includes remaining turn budget so the model can economize. |
| `MOD_HANDOFF_PROMPT` | INVITED_RESPONSE / CLOSING_STATEMENTS | 1–2 sentence spoken handoff, naming the invitee and the tension being explored; for closing statements, also states the Chair's key unresolved question on the record. |
| `CHAIR_DECISION_REVIEW_PROMPT` | DECISION_REVIEW | JSON-only over the point's record: {closeness: clear\|close, leaning, key_unresolved_question, divided_parties}. Stored in `debug_records`. |
| `CHAIR_RULING_PROMPT` | POINT_RULING | The **decision contract** (§6.3): commit to one course of action; "it depends"/split-the-difference blends prohibited; name rejected alternatives and why; record dissent as overruled or accommodated; tie-break order = user PriorityUpdates > persona weights > own judgment; still-close ⇒ rule anyway + low-confidence/reversible flag + validation follow-up task. Dual output: spoken ruling (≤300 words) + `PointResolution` JSON. States the decision hierarchy (User > Chair > Personas). |
| `CHAIR_CHALLENGE_PROMPT` | challenge intervention | One turn: revise the ruling (with updated `PointResolution`) or defend it by restating the decisive reasoning — never both, never more than once. A reaffirmed challenge becomes a recorded `sponsor_override`; do not re-argue. |
| `MOD_INTERVENTION_ACK_PROMPT` | intervention drain | Classify intent if untyped; acknowledge; state concrete effect; emit `PriorityUpdate` JSON when it's an override (binding on the Chair). Routes challenges to the Chair. |
| `MOD_IMPACT_OPEN_PROMPT` | IMPACT_OPEN | Announces decisions are final; renders the decision log (rulings + dissent dispositions + sponsor overrides) on the record; invites each persona in turn for an impact statement. Neutral, procedural. |
| `PERSONA_IMPACT_PROMPT` | IMPACT_STATEMENT | Persona-turn variant: given the full decision log, report from your domain — Additional work · Concrete steps · Considerations/risks · Dependencies on other functions · Anything else relevant. Disagree-and-commit clause for overruled personas (do not re-argue). Dual output: spoken statement + structured `impact_statement` JSON incl. optional one-line `blocking_concern`. |
| `CHAIR_REPORT_PROMPT` | SYNTHESIS (call 1) | The **full report**: problem, per-point discussion summary, each decision with its rationale, important dissent (with dispositions), impact summaries, consolidated/deduplicated action items with owners/priority/timeline (merging impact-round work items), follow-up tasks & open questions, way forward. Sponsor overrides reported verbatim, not re-litigated. |
| `CHAIR_BRIEF_PROMPT` | SYNTHESIS (call 2) | The **decision brief**, distilled from the finished report + resolutions: each decision in 1–2 lines; unresolved items (incl. any `blocking_concern`s); close/reversible rulings with their validation tasks; cross-functional dependencies from the impact round. Hard length cap (~1 page / ~400 words). Introduces no content absent from the report. |
| `WRAP_QA_PROMPT` | WRAP_QA | Route a user question to the Chair or a named persona; answer grounded in the discussion record. |
| `CHAIR_AMENDED_DOCS_PROMPT` | regenerate-docs (post-session) | Re-issue report + brief with all sponsor amendments applied: amended decisions presented as current, with the original ruling noted as overridden by the sponsor (with reason, if given) — never erased. Output headed "Amended <date>". No new judgments — the Chair records the sponsor's decisions; it does not argue with them. |
| `PRECEDENT_BLOCK` (template) | fixed header, when precedents exist | Renders the Standing Decisions snapshot with per-decision status. Audience-specific clause appended: **personas** — "settled ground: argue within these; do not re-litigate; if the current problem genuinely invalidates one, flag `precedent_conflict` (once) and move on"; **Chair** — "your agenda and rulings must be consistent with binding precedents; cite a precedent whenever it constrains your outcome"; **agenda ruling** — "reject challenge proposals that contradict a binding precedent, citing it". Open/released precedents are marked as revisitable. |
| `DISCUSSION_TITLE_PROMPT` | after confirm | Reuse `generate_conversation_title()` as-is. |

Formatting contracts that code parses (JSON schemas, the dual spoken+JSON ruling format) live in these prompts — the same edit-in-prompts-not-in-code rule the project already follows for `FINAL RANKING:`.

---

## 10. Failure Handling

| Failure | Behavior |
|---|---|
| Persona model call fails (after 1 retry) | Moderator turn on the record: "<Persona> is unavailable; noting their prior stated position." Point continues. If the *lead* fails on its statement, Moderator offers the user (via a gate-like `state` payload) to retry, reassign the persona's model, or skip the point. |
| Structured Moderator call unparseable | One re-ask with "return only JSON". Then defaults: CONFLICT_CHECK → invite all non-lead personas in weight order (capped by budget); FLOW_DECISION → `to_chair`. |
| Create request lists a precedent id that isn't a COMPLETED discussion | 400 with the offending id; nothing is created. |
| Precedent session deleted after linking | No effect — the new session holds a snapshot, never a live reference. |
| Persona fails its agenda-challenge turn (after 1 retry) | Recorded as a pass with a note; the round continues. |
| `AGENDA_RULING` JSON unparseable | One re-ask, then default: no proposals admitted, all marked `rejected (ruling unparseable)` — the user sees them in the challenge log at the gate and can re-add manually. Never silently drop proposals. |
| `DECISION_REVIEW` unparseable | One re-ask, then treat as `clear` (skip closing statements, go straight to ruling). |
| `PointResolution` JSON missing from ruling | One re-ask, then store the spoken ruling text as `decision`, empty structured fields, flag `"degraded": true`. |
| Chair model call fails (after 1 retry) | Fall back to the Moderator model *for that one ruling only*, flag the resolution `"degraded": true`, and note the substitution on the record. |
| `/turn` while a turn is generating | 409; client treats as "in flight" and re-polls session. |
| Server restart mid-discussion | Session JSON is write-through; rehydrate and continue. A turn that died mid-generation simply never happened (no partial writes). |
| User closes tab | Nothing generates (client-driven turns) — the session naturally freezes and resumes on return. This is a *feature* of the transport choice. |
| Budget exhausted | Forced ruling/synthesis with on-record acknowledgment (§6.6). |
| Attachment not usable (PDF text extraction fails; image attached but persona's model is not multimodal) | Upload succeeds with a warning surfaced in the UI; the briefing block notes "attachment <name> could not be read" so the persona (and user) know it's not in play. Never silently drop content. |
| Persona fails its impact statement (after 1 retry) | Moderator notes it on the record; the report lists that persona's impact as "not obtained"; session continues. |
| All models for a point fail | Point marked `skipped` with a transcript note; session continues; surfaced in synthesis follow-ups. |

---

## 11. Build Plan (step-by-step, for an AI implementer)

Each phase is a working increment with acceptance criteria. Do not reorder. Commit per phase.

### Phase 1 — Core orchestrator + state machine (no UI)
- `discussion.py`: session dataclass, state machine (§6.1–6.4, incl. the agenda challenge round) **with the two-agent split (Moderator + Chair as separate prompt contexts and configurable models)**, budgets, transcript, JSON persistence in `data/discussions/`. Text-only persona briefings supported in prompt assembly from day one (attachments come in Phase 5).
- All prompts from §9 in `prompts.py`.
- Config additions (§7.1).
- **Smoke script** `scratch/test_live_discussion.py`: creates a session for a canned problem, auto-confirms suggested personas/agenda, loops `advance()` to completion, prints the transcript with speaker labels (moderator/chair/persona), prints the synthesis. Include a flag to force `DECISION_REVIEW` to return `close` so the closing-statements path is exercised deterministically. (Follow the existing `scratch/test_persona_council.py` style; run with `uv run python scratch/test_live_discussion.py`.)
- ✅ *Accept:* smoke script produces a coherent multi-point discussion where personas reference each other's arguments; the agenda challenge round runs before the (auto-confirmed) gate — every persona either passes or makes one ≤150-word proposal and the Chair's batch ruling admits/folds/rejects each with a reason recorded in `agenda_challenges`; every point ends with a parseable `PointResolution` that **names a decision and at least one rejected alternative** (no split-the-difference outputs in spot checks); the forced close-call run shows closing statements from the divided parties followed by a ruling flagged low-confidence/reversible with a validation follow-up; after the last ruling, every persona delivers an impact statement (overruled personas in disagree-and-commit mode) and the run ends with **both** a full report and a ≤1-page decision brief; session JSON on disk fully describes the run; budgets demonstrably cap a point (test with budget=2).

### Phase 2 — HTTP API
- All endpoints from §7.2 in `main.py`, including the per-turn SSE response (whole-turn events; no token deltas yet), gates returning state-only, the 409 in-flight guard, and intervention queueing (including `target_point` for challenges).
- ✅ *Accept:* the full flow is drivable with `curl`/httpie alone: create → suggest/confirm personas → suggest/confirm agenda → repeated `/turn` → completed session with synthesis; an `/intervene` POST between turns visibly changes the next turn; refreshing via `GET` mid-discussion returns consistent state.

### Phase 3 — Frontend: watchable step-mode discussion
- New discussion flow in the frontend: creation screen (Step 1), persona review reusing existing persona-card UI (Step 2), agenda challenge round rendered as transcript turns followed by agenda review showing the challenge log — admitted/folded/rejected badges with the Chair's reasons, rejected proposals one-click re-addable (Step 3), transcript view with moderator/chair/persona styling — Chair rulings as decision cards — and agenda rail (Step 4, **step mode only**: a "Next turn" button), impact round rendered as regular turns (Step 5), decision panel with Brief/Full-report tabs (Step 6). Sidebar lists discussions.
- ✅ *Accept:* a user can run an entire discussion from the browser clicking "Next turn", with correct attribution, colors, agenda progress, decision cards on each ruling, impact statements in the transcript, and a decision panel showing both the brief and the full report at the end.

### Phase 4 — Interventions + pacing
- Intervention composer with type chips wired to `/intervene`; all nine behaviors from §4.2 including **challenge decision** and text-only **brief persona** (Step-2 briefing text field also lands here). Auto-advance loop with configurable gap, Pause/Resume, mode toggle.
- ✅ *Accept:* during auto-advance, submitting a priority override results (within one turn) in a Moderator acknowledgment that names the override, and subsequent Chair rulings reflect it; challenging a ruling produces exactly one revise-or-defend Chair turn, and reaffirming records a sponsor override on the resolution; a text briefing to one persona shows up as a delivery stub in the transcript and demonstrably informs that persona's next turn (and no other persona's); skip and end-discussion work; pause halts generation within one turn.

### Phase 5 — Wrap-up Q&A, export, attachments, precedents, amendments, resilience polish
- WRAP_QA state + UI; markdown export — transcript, full report, and decision brief as separate exports (all including sponsor overrides); **precedent sessions** (§4.5): creation param + snapshotting, `PRECEDENT_BLOCK` in prompt assembly, precedent-consistency clauses in agenda/challenge/ruling prompts, `precedent_conflict` flags, release-via-override, Step-1 picker UI with per-decision binding/open toggles, and the pinned Standing Decisions card; **post-session amendments** (§4.6): `/amend` + `/regenerate-docs` endpoints, append-only `amendments[]`, Override actions on decision cards with sponsor-amended badges, amendment overlay in exports; **briefing attachments**: the multipart upload endpoint, PDF/txt/md text extraction, image pass-through for multimodal persona models, briefing indicators in the cast strip; failure-handling paths from §10 exercised (kill a model id to test degradation, including the Chair-model fallback and an unreadable attachment); title generation; delete.
- ✅ *Accept:* export produces a self-contained markdown decision document; a persona with an invalid model id degrades per §10 without ending the session; an invalid Chair model id falls back to the Moderator model for the ruling and flags it degraded; a PDF briefed to one persona is cited by that persona in discussion; an image briefed to a non-multimodal persona surfaces a visible warning rather than silently vanishing; a session chained to a completed one shows personas acknowledging (not re-arguing) the standing decision, an agenda that doesn't re-open it, and a Chair ruling citing it where it constrains the outcome — and deleting the old session afterwards changes nothing; overriding a decision in a completed session preserves the original ruling under a sponsor-amended badge, a session chained *after* the amendment inherits the amended decision, and regenerate-docs produces an "Amended" report/brief with the old versions retained in history.

### Phase 6 — Nice-to-haves (only after 1–5)
- Token-level streaming of the active turn (SSE deltas). Chair and Moderator models selectable in UI (also closes the `ideas-scratchpad.md` chairman-selectable item). Per-session budget editor. UI toggle to inspect `debug_records` (conflict checks, decision reviews). "Re-open point" beyond the single challenge exchange. Conflict-heat indicator on the agenda rail.

### Phase 7 — Airtime-budget experiment (§13)
- The airtime mechanic behind its config flag (wallet, spend-or-pass call, half-rate assigned duties, floor allotment), UI toggle + pool size at creation, cast-strip meters, grant-airtime intervention; then the A/B harness `scratch/ab_test_airtime.py`, automatic metrics, and the blind LLM judge.
- ✅ *Accept:* per §13.3 — flag off ⇒ behavior identical to v3; flag on ⇒ recorded passes and floor-allotment duties observable in a low-pool run; harness emits a paired metrics + blind-judge report over ≥3 problems.

---

## 12. Cost & Latency Expectations (set user expectations in UI)

Rough per-session call count with defaults (5 points, 4 personas, ~6 persona turns/point average):
- Setup: ~3 calls (personas, agenda, title) + agenda challenge round: 1 open + 1 per persona + 1 ruling ≈ 6
- Per point: 1 open + 1 lead + 1 conflict-check + ~4 invited/rebuttal + ~3 flow-decisions + 1 decision-review + 0–2 closing statements + 1 ruling ≈ 12–14 → ~65 for 5 points
- Impact round: 1 open + 1 per persona ≈ 5
- Synthesis (report + brief) + acks/challenges: ~7
- **Total ≈ 80–95 calls**, most of them short and most on the cheap Moderator model — cost is dominated by persona turns and Chair rulings/synthesis. This exceeds a Persona-mode run (~10 calls) several-fold; the turn-budget indicator and the session hard cap exist precisely for this, and the UI should show a running call count.

Latency per turn ≈ one model call (2–15s). Auto-advance therefore feels like a real chat with people typing — that's desirable, not a bug to optimize away.

---

## 13. Experimental Mechanic: Persona Airtime Budgets (optional, A/B-tested)

**Hypothesis.** Giving each persona a finite airtime wallet for the whole discussion creates opportunity cost: speaking on point 2 means less capacity to fight on point 4. That scarcity should force conviction-driven prioritization — personas concede cheap points quickly, pass on invitations they don't care about, and spend heavily only where their expertise says the stakes are real. Passing itself becomes signal: "the Security Architect saved their airtime for this point" tells the Chair something no prompt exhortation can.

**Honest counter-hypothesis (why this must be A/B-tested, not just shipped).** LLMs don't *feel* scarcity — a balance number in the prompt may change nothing, or backfire: personas may hoard and under-participate, clip arguments below usefulness, or game the accounting. Any real effect must come from **structure** (an explicit spend-or-pass decision before each elective turn, and hard `max_tokens` ceilings), not from pleading in the prompt. This is exactly the kind of mechanic that sounds right and needs evidence — hence the framework below. Off by default; per-session user option either way.

### 13.1 Design (when `airtime.enabled` for a session)

- **Wallet.** Each persona gets an allotment in words, from a session pool (default 2,000 words) split **proportionally to numeric `weight`** — this finally makes weight mean something personas can feel, not just a Chair-side tiebreaker.
- **What costs airtime.** Elective speech at full rate: accepting an invitation, rebuttals, replies. **Assigned duties at half rate:** lead statements, closing statements, impact statements — the persona didn't choose them, and the meeting can't function if they're silenced; at zero balance, assigned duties still get a minimum floor allotment (e.g. 100 words). Passing is free. The agenda challenge round (§6.2) is free — it precedes the discussion and already carries its own scarcity mechanism (one shot).
- **Spend-or-pass decision.** When invited to speak electively, the persona first makes a cheap structured call: `{action: speak|pass, words_requested, one_line_reason}` given its balance and the point at stake. A pass goes on the record via the Moderator ("<Persona> defers, conserving their remaining airtime") — visible prioritization. A speak sets that turn's `max_tokens` to `min(words_requested, balance, per-turn cap)`.
- **No mid-sentence truncation.** The budget gates *whether and how long* a persona speaks (declared before the turn), never chops rendered text; the turn prompt states the allotment so the model composes to fit.
- **Visibility.** A persona sees only its own balance. Moderator and Chair see all balances — spending patterns are decision-relevant signal ("X went quiet for three points to fight here; weigh accordingly", stated in `CHAIR_RULING_PROMPT` when the mechanic is on). Other personas see passes (they're on the record) but not balances. UI: airtime meters on the cast strip.
- **User control.** Toggle + pool size at session creation (Step 1); mid-discussion the user can **grant additional airtime** to any persona (extension of the Brief-persona intervention: `{grant_words}`) — the sponsor giving someone more time at the mic.
- **New/changed pieces:** `config.airtime {enabled, pool_words, weight_proportional}`; `personas[].airtime {allotted, spent}`; transcript `meta.words_spent`; new turn type `pass`; new prompt `PERSONA_SPEND_DECISION_PROMPT` (JSON-only, uses the persona's own model); one added line in `PERSONA_TURN_PROMPT` stating the allotment. Parse failure on a spend decision defaults to `speak` at the per-turn cap (never silence a persona on a parse error).

### 13.2 A/B Experiment Framework (budget vs. no-budget)

1. **Variant tagging (observational).** Every session JSON records its `airtime` config; every in-product session is automatically a labeled sample. At session end, a one-tap quality rating ("How useful was this discussion?" 1–5) is stored beside the variant tag.
2. **Paired-run harness (controlled).** `scratch/ab_test_airtime.py`: takes a problem spec (or a directory of them); runs persona suggestion + agenda **once**, freezes personas/models/weights/agenda; then runs the discussion **twice** with identical inputs — variant A (budget off) and variant B (budget on) — and writes both session JSONs side by side. Everything except the mechanic is held constant. A corpus of 5–10 diverse problems is enough for a first read.
3. **Automatic metrics** (computed from session JSONs, no LLM): mean words per persona turn; turns and elective turns per point; pass rate; participation spread across personas (did anyone go silent?); concessions (from the structured record); total tokens/cost; wall-clock.
4. **Blind LLM judge.** An evaluator model — deliberately *not* any model used in the council, to reduce affinity bias — receives the two transcripts labeled only "Discussion A"/"Discussion B" (order randomized per pair, variant hidden; same anonymization discipline as Stage 2) and scores each 1–5 with one-line justifications on: argument specificity, redundancy (reverse-scored), genuine engagement with opposing points, clarity of prioritization, and decision quality of the rulings; plus an overall preference. JSON output, parsed tolerantly.
5. **Report + decision rule (stated in advance).** The harness prints a paired comparison table (metrics + judge scores per problem, aggregate deltas). Adopt budget-on as the default only if it wins on judge quality without dropping participation spread by more than ~20%; keep it as a user option if results are mixed; drop the mechanic if it loses on quality — regardless of how elegant the theory is.

### 13.3 Build placement

Implement as **Phase 7** (after Phase 6): the mechanic behind its config flag, the spend-or-pass call, UI toggle + meters + grant-airtime, then the harness, metrics, and judge. ✅ *Accept:* with the flag off, sessions are byte-identical in behavior to v3; with it on, a forced low-pool run shows recorded passes and a floor-allotment lead statement; the harness produces a paired report with metrics and blind judge scores for at least 3 problems.

---

## 14. Open Questions (decide before/while building; defaults given)

1. **Should personas see each persona's numeric weight?** Default **no** — weights inform only the Chair's rulings (mirrors existing Stage 3 design; prevents personas from deferring pre-emptively).
2. **Structured-call visibility (conflict checks, decision reviews).** Default: not in the transcript, but stored in `debug_records` and inspectable — consistent with the project's "all raw outputs inspectable" transparency principle. UI toggle is a Phase 6 item.
3. **Re-opening resolved points beyond the single challenge exchange.** Default v1: the one revise-or-defend challenge turn, plus wrap-up Q&A; full re-litigation is a Phase 6 candidate (budget protection).
4. **Discussions and conversations in one sidebar list or two sections?** Default: one list, type-badged.
5. **Minimum viable persona count.** Default 3 (a 2-persona "discussion" is a debate; still allow it, but the suggestion prompt targets 3–5).
6. **Should the Chair's `leaning` from DECISION_REVIEW ever be shown to personas before closing statements?** Default **no** — only the *key unresolved question* is stated on the record. Revealing the leaning would invite sycophantic convergence toward it instead of genuine final arguments.
7. **Should the Chair (or other personas) see a persona's briefing contents?** Default **no** — briefings are private to the briefed persona; facts from them enter the record only through that persona's spoken arguments, exactly like an expert's private knowledge in a real meeting. The transcript's delivery stub keeps the *existence* of the briefing on the record. Revisit if users find rulings ignore un-voiced briefing facts (the fix would be a user choice per briefing: private vs. on the record).
8. **Airtime accounting unit (§13): words or model tokens?** Default **words** — model-agnostic (personas run on different tokenizers), human-legible in the UI, and enforcement via `max_tokens` can approximate (≈1.4 tokens/word) since the ceiling is a composition target, not a truncation point.
9. **Should assigned duties (lead/closing/impact) cost airtime at all?** Default half rate with a zero-balance floor (§13.1) — free would let a persona rebut infinitely via its lead role on later points; full rate could silence a heavily-weighted persona's obligations. Revisit with A/B data.
10. **Can personas argue for agenda *removals* or reordering in the challenge round?** Default **additions only** — a persona arguing to remove a point is a conflict that belongs in the discussion of that point, and reordering is the Chair's/user's call. Revisit if challenge logs show personas folding removal arguments into addition proposals.
11. **What if two linked precedent sessions contradict each other?** Default: detect overlap at creation (cheap structured check over the two decision snapshots), surface the conflict to the user in the picker, and require them to set one side to `open` before the session starts. Silently letting the newest win hides a real organizational conflict from the person who owns it.

---

## 15. Success Criteria (product-level)

1. A non-technical user can go from problem → confirmed cast → confirmed agenda → watched discussion → decision package without reading docs.
2. In ≥80% of sessions on real prompts, at least one persona *changes or concedes a position* in response to another's argument — the debate is real, not parallel monologues (spot-check qualitatively).
2a. The agenda challenge round produces genuine selectivity: across sessions, personas sometimes pass and the Chair sometimes rejects — if every persona always proposes and every proposal is always admitted, the one-shot mechanism isn't discriminating (tune `CHAIR_AGENDA_RULING_PROMPT`'s bar).
3. **Rulings are decisive:** in spot checks, every `PointResolution` commits to a single course of action and names at least one rejected alternative; zero split-the-difference non-decisions.
4. A user intervention mid-discussion is acknowledged within one turn and demonstrably alters at least the current point's ruling; a challenged ruling gets exactly one revise-or-defend response, and a reaffirmed challenge is recorded as a sponsor override.
5. Every completed session (impact round not skipped) contains one impact statement per persona, each naming at least one concrete work item or dependency — and overruled personas' statements execute the decision rather than re-arguing it.
6. Every completed session yields **both** closing documents: a full report and a decision brief ≤1 page, plus ≥1 action item with an owner and a per-point decision log. The brief contains every decision, every unresolved item, and every close/reversible call — and nothing that isn't in the report.
7. In precedent-linked sessions, binding precedents are never re-litigated (spot-check: personas reference them as settled, dissents about them arrive only as `precedent_conflict` flags) and every Chair ruling that a precedent constrains cites it explicitly.
8. Post-session amendments are append-only in practice: no code path mutates or deletes an original ruling, action item, or document version — every prior value is recoverable from `amendments[]` and `synthesis.history`.
9. No session exceeds its hard call cap; no single model failure ends a session.
