import asyncio
import os
import sys

# Add the parent directory of backend to Python path to allow importing backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import COUNCIL_MODELS
from backend.council import suggest_personas, run_full_council

async def test():
    query = "Should we build our backend with Node.js/Express or Python/FastAPI?"
    print(f"--- Suggesting Personas for Query: '{query}' ---")
    personas = await suggest_personas(query)

    # Exercise the per-persona model assignment + numeric weight feature,
    # mimicking what the frontend would set on the Persona screen.
    weights = [0.5, 0.3, 0.2]
    for i, p in enumerate(personas):
        p['model'] = COUNCIL_MODELS[i % len(COUNCIL_MODELS)]
        p['weight'] = weights[i % len(weights)]

    for i, p in enumerate(personas, start=1):
        print(f"\nPersona {i}: {p['name']} (Model: {p['model']}, Weight: {p['weight']})")
        print(f"Weightage: {p['weightage']}")
        print(f"Facets: {p['facets']}")

    print("\n--- Running Full Council with Personas (Round-Robin Mapping) ---")
    stage1, stage2, stage3, metadata = await run_full_council(
        query,
        mode="persona",
        personas=personas,
        mapping_option="round_robin"
    )

    print("\n--- STAGE 1 RESULTS ---")
    for r in stage1:
        print(f"\nModel: {r['model']} (Persona: {r.get('persona')}, Weight: {r.get('persona_weight')})")
        print(f"Response (truncated): {r['response'][:200]}...")

    print("\n--- STAGE 2 RESULTS ---")
    for r in stage2:
        print(f"\nModel: {r['model']}")
        print(f"Ranking:\n{r['ranking']}")

    print("\n--- STAGE 3 RESULTS ---")
    print(f"Chairman Model: {stage3['model']}")
    print(f"Final Response:\n{stage3['response']}")

    print("\n--- METADATA ---")
    print(metadata)

if __name__ == "__main__":
    asyncio.run(test())
