"""
Data analysis agent with code execution.
"""

import anthropic
import subprocess
import tempfile
import sys
import argparse
from pathlib import Path

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"
DATA_DIR = Path(__file__).parent / "data"

tools = [
    {
        "name": "execute_python",
        "description": """Execute Python code for data analysis.

Pre-loaded:
- pandas as pd
- matplotlib.pyplot as plt
- df: the dataset as a DataFrame

Start by exploring df.head() and df.dtypes to understand the schema.
Use print() for output. Use plt.savefig('chart.png') for charts.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "goal": {"type": "string", "description": "What this analysis step accomplishes"}
            },
            "required": ["code", "goal"]
        }
    }
]


def execute_python(code: str, data_file: str = "campaigns.csv") -> str:
    """Run Python code with pandas and data pre-loaded."""

    wrapper = f'''
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv("{DATA_DIR / data_file}")

{code}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(wrapper)
        f.flush()
        try:
            result = subprocess.run(
                [sys.executable, f.name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path(__file__).parent
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            return output if output.strip() else "(no output)"
        except subprocess.TimeoutExpired:
            return "[error]: execution timed out"
        except Exception as e:
            return f"[error]: {e}"


def run_agent(question: str, system_prompt: str, data_file: str = "campaigns.csv", verbose: bool = True) -> str:
    """Run analysis agent with given prompt."""

    messages = [{"role": "user", "content": question}]

    if verbose:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print('='*60)

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            final = "".join(b.text for b in response.content if hasattr(b, "text"))
            if verbose:
                print(f"\n[Answer]\n{final}")
            return final

        tool_results = []
        for block in response.content:
            if hasattr(block, "text") and block.text and verbose:
                print(f"\n[Thinking] {block.text}")

            if block.type == "tool_use":
                if verbose:
                    print(f"\n[{block.input.get('goal', 'analyzing')}]")
                    print(f"```python\n{block.input['code']}\n```")

                result = execute_python(block.input["code"], data_file)

                if verbose:
                    preview = result[:400] + "..." if len(result) > 400 else result
                    print(f">>> {preview}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})


def load_prompt(version: str) -> str:
    """Load a prompt version from prompts/"""
    module = __import__(f"prompts.{version}", fromlist=["SYSTEM_PROMPT"])
    return module.SYSTEM_PROMPT


def main():
    parser = argparse.ArgumentParser(description="Data analysis agent")
    parser.add_argument("--prompt", "-p", default="v2_structured", help="Prompt version (v1_basic, v2_structured, v3_analytical)")
    parser.add_argument("--data", "-d", default="campaigns.csv", help="Data file in data/")
    parser.add_argument("--question", "-q", help="Single question (non-interactive)")
    args = parser.parse_args()

    system_prompt = load_prompt(args.prompt)

    if args.question:
        run_agent(args.question, system_prompt, args.data)
        return

    print(f"\nData Analysis Agent (prompt: {args.prompt})")
    print("="*40)

    while True:
        try:
            question = input("\nYou: ").strip()
            if question.lower() in ('exit', 'quit', 'q'):
                break
            if question:
                run_agent(question, system_prompt, args.data)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
