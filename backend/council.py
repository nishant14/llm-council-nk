"""3-stage LLM Council orchestration."""

import json
import re
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from .prompts import (
    PERSONA_SUGGESTION_PROMPT,
    CONVERSATION_TITLE_PROMPT,
    STAGE1_PERSONA_SYSTEM_PROMPT,
    STAGE2_STANDARD_RANKING_PROMPT,
    STAGE2_PERSONA_RANKING_PROMPT,
    STAGE3_STANDARD_CHAIRMAN_PROMPT,
    STAGE3_PERSONA_CHAIRMAN_PROMPT
)


async def stage1_collect_responses(
    user_query: str,
    mode: str = "standard",
    personas: Optional[List[Dict[str, str]]] = None,
    mapping_option: Optional[str] = "round_robin"
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        mode: "standard" or "persona"
        personas: Optional list of personas
        mapping_option: "round_robin" or "matrix"

    Returns:
        List of dicts with 'model', 'response', and optional 'persona' keys
    """
    if mode != "persona" or not personas:
        messages = [{"role": "user", "content": user_query}]

        # Query all models in parallel
        responses = await query_models_parallel(COUNCIL_MODELS, messages)

        # Format results
        stage1_results = []
        for model, response in responses.items():
            if response is not None:  # Only include successful responses
                stage1_results.append({
                    "model": model,
                    "response": response.get('content', '')
                })

        return stage1_results

    # Persona flow
    queries_to_make = []

    if mapping_option == "round_robin":
        # Option C: Assign personas sequentially across council models
        for i, model in enumerate(COUNCIL_MODELS):
            persona = personas[i % len(personas)]
            system_prompt = STAGE1_PERSONA_SYSTEM_PROMPT.format(
                persona_name=persona['name'],
                persona_weightage=persona['weightage'],
                persona_facets=persona['facets']
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
            queries_to_make.append((model, persona['name'], messages))
    else:  # "matrix"
        # Option B: Every model answers from every persona's perspective
        for persona in personas:
            for model in COUNCIL_MODELS:
                system_prompt = STAGE1_PERSONA_SYSTEM_PROMPT.format(
                    persona_name=persona['name'],
                    persona_weightage=persona['weightage'],
                    persona_facets=persona['facets']
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
                queries_to_make.append((model, persona['name'], messages))

    # Query in parallel
    async def query_with_metadata(model, persona_name, msgs):
        res = await query_model(model, msgs)
        return {
            "model": model,
            "persona": persona_name,
            "response": res.get('content', '') if res else ''
        }

    futures = [query_with_metadata(m, p, msgs) for m, p, msgs in queries_to_make]
    results = await asyncio.gather(*futures)

    # Filter out empty responses
    return [r for r in results if r["response"]]


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    mode: str = "standard"
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        mode: "standard" or "persona"

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = []
    for i in range(len(stage1_results)):
        if i < 26:
            labels.append(chr(65 + i))  # A, B, C...
        else:
            labels.append(f"Z{i-25}")  # Fallback just in case

    # Create mapping from label to model name
    label_to_model = {}
    for label, result in zip(labels, stage1_results):
        model_name = result['model']
        if result.get('persona'):
            model_name = f"{model_name} ({result['persona']})"
        label_to_model[f"Response {label}"] = model_name

    # Build the ranking prompt
    if mode == "persona":
        responses_text = "\n\n".join([
            f"Response {label} (Persona/Perspective: {result.get('persona', 'N/A')}):\n{result['response']}"
            for label, result in zip(labels, stage1_results)
        ])
        ranking_prompt = STAGE2_PERSONA_RANKING_PROMPT.format(
            user_query=user_query,
            responses_text=responses_text
        )
    else:
        responses_text = "\n\n".join([
            f"Response {label}:\n{result['response']}"
            for label, result in zip(labels, stage1_results)
        ])
        ranking_prompt = STAGE2_STANDARD_RANKING_PROMPT.format(
            user_query=user_query,
            responses_text=responses_text
        )

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    mode: str = "standard"
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        mode: "standard" or "persona"

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    if mode == "persona":
        stage1_text = "\n\n".join([
            f"Model: {result['model']} (Persona/Perspective: {result.get('persona', 'N/A')})\nResponse: {result['response']}"
            for result in stage1_results
        ])

        stage2_text = "\n\n".join([
            f"Model: {result['model']}\nRanking: {result['ranking']}"
            for result in stage2_results
        ])

        chairman_prompt = STAGE3_PERSONA_CHAIRMAN_PROMPT.format(
            user_query=user_query,
            stage1_text=stage1_text,
            stage2_text=stage2_text
        )
    else:
        stage1_text = "\n\n".join([
            f"Model: {result['model']}\nResponse: {result['response']}"
            for result in stage1_results
        ])

        stage2_text = "\n\n".join([
            f"Model: {result['model']}\nRanking: {result['ranking']}"
            for result in stage2_results
        ])

        chairman_prompt = STAGE3_STANDARD_CHAIRMAN_PROMPT.format(
            user_query=user_query,
            stage1_text=stage1_text,
            stage2_text=stage2_text
        )

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def suggest_personas(user_query: str) -> List[Dict[str, str]]:
    """
    Generate 3 expert personas (perspectives) for a given user query.

    Args:
        user_query: The user's question or problem description

    Returns:
        List of 3 dictionaries containing 'name', 'weightage', and 'facets'
    """
    prompt = PERSONA_SUGGESTION_PROMPT.format(user_query=user_query)
    messages = [{"role": "user", "content": prompt}]
    
    # Query using gemini-2.5-flash
    response = await query_model("google/gemini-2.5-flash", messages, timeout=45.0)
    
    default_personas = [
        {
            "name": "Technical Architect",
            "weightage": "Focus heavily on software design patterns, complexity, robustness, and architectural scalability.",
            "facets": "Considerations: Technical complexity, scaling constraints, framework choices. Note: This list is not exhaustive and should be thought through by the model."
        },
        {
            "name": "User Experience Designer",
            "weightage": "Focus heavily on user convenience, clarity of interaction, and cognitive load of the solution.",
            "facets": "Considerations: User friction, simplicity, accessibility. Note: This list is not exhaustive and should be thought through by the model."
        },
        {
            "name": "Product & Cost Analyst",
            "weightage": "Focus heavily on execution cost, delivery timeline, maintenance overhead, and overall business value.",
            "facets": "Considerations: Execution speed, API costs, maintenance complexity. Note: This list is not exhaustive and should be thought through by the model."
        }
    ]
    
    if response is None or not response.get('content'):
        return default_personas
        
    content = response['content'].strip()
    
    # Clean JSON format
    try:
        # Strip markdown json code block if present
        clean_content = re.sub(r'^```(?:json)?\s*', '', content)
        clean_content = re.sub(r'\s*```$', '', clean_content)
        data = json.loads(clean_content)
        if "personas" in data and isinstance(data["personas"], list) and len(data["personas"]) == 3:
            return data["personas"]
    except Exception as e:
        print(f"Error parsing generated personas JSON: {e}")
        
    return default_personas


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = CONVERSATION_TITLE_PROMPT.format(user_query=user_query)

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    mode: str = "standard",
    personas: Optional[List[Dict[str, str]]] = None,
    mapping_option: Optional[str] = "round_robin"
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        mode: "standard" or "persona"
        personas: Optional list of personas
        mapping_option: "round_robin" or "matrix"

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(
        user_query,
        mode=mode,
        personas=personas,
        mapping_option=mapping_option
    )

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query,
        stage1_results,
        mode=mode
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        mode=mode
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
