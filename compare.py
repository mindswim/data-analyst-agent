"""
Compare prompt versions on the same questions.
"""

import json
from datetime import datetime
from pathlib import Path
from agent import run_agent, load_prompt

EVAL_QUESTIONS = [
    "Which campaign has the best CPA?",
    "How does performance vary by channel?",
    "What trends do you see over time?",
    "Where should we reallocate budget to improve overall ROAS?",
]


def compare_prompts(prompt_versions: list[str], questions: list[str] = None, data_file: str = "campaigns.csv"):
    """Run same questions across prompt versions and save results."""

    questions = questions or EVAL_QUESTIONS
    results = {
        "timestamp": datetime.now().isoformat(),
        "data_file": data_file,
        "comparisons": []
    }

    for question in questions:
        comparison = {"question": question, "responses": {}}

        for version in prompt_versions:
            print(f"\n{'='*60}")
            print(f"[{version}] {question}")
            print('='*60)

            prompt = load_prompt(version)
            response = run_agent(question, prompt, data_file, verbose=True)
            comparison["responses"][version] = response

        results["comparisons"].append(comparison)

    # Save results
    output_file = Path(__file__).parent / "data" / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_file}")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare prompt versions")
    parser.add_argument("--prompts", "-p", nargs="+", default=["v1_basic", "v2_structured", "v3_analytical"])
    parser.add_argument("--questions", "-q", nargs="+", help="Custom questions (default: built-in eval set)")
    parser.add_argument("--data", "-d", default="campaigns.csv")
    args = parser.parse_args()

    compare_prompts(args.prompts, args.questions, args.data)
