"""Central repository for all LLM prompt templates used in LLM Council."""

# Prompt used to suggest 3 expert personas for a given query (Stage 0)
PERSONA_SUGGESTION_PROMPT = """You are an assistant that analyzes a user's question and suggests 3 expert personas (perspectives) that should analyze this question to provide a comprehensive, multi-dimensional answer.

For each persona, you must provide:
1. A descriptive name (e.g. "Security Architect", "UX Specialist", "Cost Optimization Consultant").
2. Focus/Weightage: Explicit instructions telling the model to give more weightage to a particular perspective or set of constraints (e.g. security/privacy, user convenience, deployment/operational costs) rather than just stating general expertise.
3. Facets/Considerations: A list of key topics or questions that are important to consider from this perspective. It must explicitly state that this list is not exhaustive and that the model should think through other relevant facets.

User Question: {user_query}

You MUST return the output as a valid JSON object. Ensure it has exactly 3 personas. Do not write markdown blocks or text around it. Use this format:
{{
  "personas": [
    {{
      "name": "Persona Name",
      "weightage": "Focus instruction (e.g., Give maximum weightage to security/privacy, prioritizing data exposure risk and operational integrity over UX convenience.)",
      "facets": "Considerations: [Facet 1], [Facet 2], [Facet 3]. Note: This list is not exhaustive and should be thought through by the model."
    }},
    {{
      "name": "...",
      "weightage": "...",
      "facets": "..."
    }},
    {{
      "name": "...",
      "weightage": "...",
      "facets": "..."
    }}
  ]
}}"""

# Prompt used to generate a short conversation title from the first message
CONVERSATION_TITLE_PROMPT = """Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

# System prompt for individual models answering under a specific persona in Stage 1
STAGE1_PERSONA_SYSTEM_PROMPT = """You are an expert answering a user's question from a specific perspective.
Your Persona: {persona_name}
Focus/Weightage: {persona_weightage}
Important considerations (not exhaustive): {persona_facets}

Answer the user query thoroughly and professionally from this perspective."""

# Prompt for peer ranking and critiques in Stage 2 (Standard mode)
STAGE2_STANDARD_RANKING_PROMPT = """You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. For each response, score it from 1-5 on each of the following criteria, with a one-line justification per criterion:
   - Accuracy/correctness: Is the response factually correct, free of hallucinations or errors?
   - Depth & completeness: Does it thoroughly cover the relevant aspects of the question, without being superficial?
   - Actionability/practical value: Does it give the user something concretely usable, not just abstract discussion?
2. Evaluate purely on these criteria. Do not favor a response for being longer or more elaborately styled if it isn't more substantive. The responses are anonymized — do not assume any response is your own and do not treat it differently if you suspect it is.
3. Then, at the very end of your response, provide a final ranking informed by your scoring above.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A:
- Accuracy/correctness: 4/5 - mostly correct, one minor factual slip
- Depth & completeness: 3/5 - covers X but misses Y
- Actionability/practical value: 4/5 - gives clear next steps

Response B:
- Accuracy/correctness: 5/5 - fully accurate
- Depth & completeness: 3/5 - lacks depth on Z
- Actionability/practical value: 3/5 - mostly conceptual, fewer concrete steps

Response C:
- Accuracy/correctness: 5/5 - fully accurate
- Depth & completeness: 5/5 - most comprehensive
- Actionability/practical value: 5/5 - highly actionable

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

# Prompt for peer ranking and critiques in Stage 2 (Persona mode)
STAGE2_PERSONA_RANKING_PROMPT = """You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized LLM identities), along with their assigned expert personas:

{responses_text}

Your task:
1. For each response, score it from 1-5 on each of the following criteria — judged from the response's assigned persona's perspective — with a one-line justification per criterion:
   - Accuracy/correctness: Is the response factually correct, free of hallucinations or errors?
   - Depth & completeness: Does it thoroughly cover the relevant aspects of the question from its persona's perspective, without being superficial?
   - Actionability/practical value: Does it give the user something concretely usable from its persona's perspective, not just abstract discussion?
2. Evaluate purely on these criteria. Do not favor a response for being longer or more elaborately styled if it isn't more substantive. The responses are anonymized — do not assume any response is your own and do not treat it differently if you suspect it is.
3. Then, at the very end of your response, provide a final ranking informed by your scoring above.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A (Security Architect):
- Accuracy/correctness: 4/5 - solid security analysis, one outdated claim
- Depth & completeness: 4/5 - good security coverage but lacks financial detail
- Actionability/practical value: 4/5 - clear mitigations suggested

Response B (UX Designer):
- Accuracy/correctness: 5/5 - accurate UX guidance
- Depth & completeness: 3/5 - excellent UX detail but misses security concerns
- Actionability/practical value: 4/5 - concrete design recommendations

FINAL RANKING:
1. Response B
2. Response A

Now provide your evaluation and ranking:"""

# Prompt for final response synthesis by the Chairman in Stage 3 (Standard mode)
STAGE3_STANDARD_CHAIRMAN_PROMPT = """You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

# Prompt for final response synthesis by the Chairman in Stage 3 (Persona mode)
STAGE3_PERSONA_CHAIRMAN_PROMPT = """You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question from specific expert perspectives, and then reviewed and ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Persona-Based Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question.
Please consider:
- The different persona perspectives and their insights (e.g., security, UX, cost).
- Each persona's Weight (shown above, on a 0-1 scale, summing to 1 across all personas): this is the relative importance the user has assigned to that perspective. Proportionally emphasize higher-weighted perspectives in your synthesis, while still substantively addressing lower-weighted ones — do not drop them entirely.
- Explicitly highlight any trade-offs or conflicts between these perspectives and resolve them in light of their weights.
- The peer rankings and critiques.

Provide a clear, well-reasoned final answer that represents the council's collective wisdom, reflects the user's stated priorities via the weights, and resolves conflicts between the perspectives:"""
