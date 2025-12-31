"""
Chainlit UI for the data analysis agent.
Run with: chainlit run app.py
"""

import chainlit as cl
from chainlit.input_widget import Select
import anthropic
import subprocess
import tempfile
import sys
import importlib.util
from pathlib import Path

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"
DATA_DIR = Path(__file__).parent / "data"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Load available prompts
def load_prompts() -> dict[str, str]:
    """Load all prompt versions from prompts/ directory."""
    prompts = {}
    for f in PROMPTS_DIR.glob("v*.py"):
        name = f.stem
        spec = importlib.util.spec_from_file_location(name, f)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        prompts[name] = module.SYSTEM_PROMPT
    return prompts

# PROMPTS loaded dynamically in on_chat_start to pick up new versions

tools = [
    {
        "name": "execute_python",
        "description": """Execute Python code for data analysis.

Pre-loaded:
- pandas as pd
- matplotlib.pyplot as plt
- df: the dataset as a DataFrame

Start by exploring df.head() and df.dtypes to understand the schema.
Use print(df.to_markdown()) for tables. Use plt.savefig('output.png') for charts.""",
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


def get_system_prompt():
    prompts = load_prompts()
    prompt_name = cl.user_session.get("prompt_version")
    if prompt_name and prompt_name in prompts:
        return prompts[prompt_name]
    # Fallback to latest
    return prompts[sorted(prompts.keys())[-1]]


def execute_python(code: str, data_file: str = "campaigns.csv") -> tuple[str, str | None]:
    """Run Python code. Returns (output, chart_path or None)."""

    chart_path = Path(__file__).parent / "output.png"
    if chart_path.exists():
        chart_path.unlink()

    wrapper = f'''
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tabulate
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

            chart = str(chart_path) if chart_path.exists() else None
            return output if output.strip() else "(no output)", chart

        except subprocess.TimeoutExpired:
            return "[error]: execution timed out", None
        except Exception as e:
            return f"[error]: {e}", None


@cl.on_chat_start
async def start():
    # Reload prompts to pick up any new versions
    prompts = load_prompts()
    prompt_options = sorted(prompts.keys())
    latest_prompt = prompt_options[-1] if prompt_options else "v1_basic"
    settings = await cl.ChatSettings(
        [
            Select(
                id="prompt_version",
                label="Prompt Version",
                values=prompt_options,
                initial_value=latest_prompt,
            ),
        ]
    ).send()

    cl.user_session.set("prompt_version", settings["prompt_version"])
    cl.user_session.set("data_file", "campaigns.csv")
    cl.user_session.set("messages", [])

    # Add action button to view prompt
    actions = [
        cl.Action(name="show_prompt", payload={}, label="View Current Prompt"),
    ]

    await cl.Message(
        content=f"Data Analysis Agent ready. Using **{settings['prompt_version']}** prompt.\n\nAsk a question about the campaign data.",
        actions=actions
    ).send()


@cl.action_callback("show_prompt")
async def show_prompt_action(action):
    prompts = load_prompts()
    prompt_name = cl.user_session.get("prompt_version")
    prompt_text = prompts.get(prompt_name, "Prompt not found")
    await cl.Message(content=f"**{prompt_name}**\n\n```\n{prompt_text}\n```").send()


@cl.on_settings_update
async def settings_update(settings):
    cl.user_session.set("prompt_version", settings["prompt_version"])
    cl.user_session.set("messages", [])  # Reset conversation on prompt change
    await cl.Message(content=f"Switched to **{settings['prompt_version']}** prompt. Conversation reset.").send()


@cl.on_message
async def main(message: cl.Message):
    messages = cl.user_session.get("messages", [])
    messages.append({"role": "user", "content": message.content})
    data_file = cl.user_session.get("data_file", "campaigns.csv")

    while True:
        # Create message for streaming
        msg = cl.Message(content="")
        await msg.send()

        # Stream the response
        tool_use_block = None
        full_response = []

        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=get_system_prompt(),
            tools=tools,
            messages=messages
        ) as stream:
            for event in stream:
                # Handle text streaming
                if hasattr(event, 'type'):
                    if event.type == 'content_block_delta':
                        if hasattr(event.delta, 'text'):
                            await msg.stream_token(event.delta.text)
                    elif event.type == 'content_block_start':
                        if hasattr(event.content_block, 'type') and event.content_block.type == 'tool_use':
                            tool_use_block = {
                                'id': event.content_block.id,
                                'name': event.content_block.name,
                                'input': {}
                            }
                    elif event.type == 'content_block_delta':
                        if hasattr(event.delta, 'partial_json') and tool_use_block:
                            pass  # Accumulating in final_message

            final_message = stream.get_final_message()

        await msg.update()

        # Check if done
        if final_message.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": final_message.content})
            cl.user_session.set("messages", messages)
            return

        # Process tool calls
        tool_results = []
        for block in final_message.content:
            if hasattr(block, "text") and block.text:
                pass  # Already streamed

            if block.type == "tool_use":
                goal = block.input.get("goal", "Analyzing...")
                code = block.input["code"]

                async with cl.Step(name=goal, type="tool") as step:
                    step.input = f"```python\n{code}\n```"
                    output, chart_path = execute_python(code, data_file)
                    step.output = output[:1000] + "..." if len(output) > 1000 else output

                # Show chart if generated
                if chart_path:
                    elements = [cl.Image(name="chart", path=chart_path, display="inline")]
                    await cl.Message(content="", elements=elements).send()

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })

        # Add to message history
        messages.append({"role": "assistant", "content": final_message.content})
        messages.append({"role": "user", "content": tool_results})
        cl.user_session.set("messages", messages)
