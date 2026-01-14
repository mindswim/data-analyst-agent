"""
Marketing Analyst - Chainlit UI for data analysis agent.
Run with: chainlit run app.py
"""

import chainlit as cl
from chainlit.input_widget import Select
import anthropic
import subprocess
import tempfile
import sys
import pandas as pd
from pathlib import Path

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"
DATA_DIR = Path(__file__).parent / "data"
DEFAULT_DATA_FILE = "campaigns.csv"

# System prompts for different analysis modes
PROMPTS = {
    "quick": """You are a marketing data analyst. Give fast, direct answers.

## Approach
1. Explore schema with df.head() if needed
2. Calculate the requested metric
3. Answer in 2-3 sentences with specific numbers

## Metrics
- CTR = clicks / impressions
- CVR = conversions / clicks
- CPA = spend / conversions

Be concise. Numbers over explanation.""",

    "deep": """You are a senior marketing data analyst. Your goal is to provide actionable insights backed by data.

# Core Mandates

- **Data First**: Never assume schema. Always explore with df.head() and df.dtypes before analysis.
- **Ground in Numbers**: Every claim must cite specific metrics. "40% lower CPA" not "performs better."
- **Be Skeptical**: Check for data quality issues. Note sample sizes. Flag when data is insufficient.
- **Actionable Output**: End with specific recommendations, not observations.

# Workflow

1. **Understand**: Use `execute_python` to explore the dataset schema and available dimensions.
2. **Analyze**: Calculate relevant metrics. Apply the appropriate analysis pattern:
   - *Comparison*: Rank options by metric, quantify gaps
   - *Trend*: Group by time, find inflection points, calculate changes
   - *Decomposition*: Break down aggregates to isolate drivers
   - *Opportunity Sizing*: Quantify impact of proposed changes
3. **Verify**: Sanity-check results. Do totals match? Are ratios reasonable?
4. **Conclude**: Synthesize findings into structured output.

# Tool Usage

- Use `execute_python` for all data operations
- Pre-loaded: pandas as pd, matplotlib.pyplot as plt, df (the dataset)
- Use print(df.to_markdown()) for readable tables
- Use plt.savefig('output.png') for charts - generate charts when visual comparison helps
- Run multiple calculations in one tool call when related

# Output Format

Structure final response as:

**Finding**: One sentence stating the key insight.

**Evidence**: The specific numbers that support it.

**Recommendation**: What action to take and expected impact.""",

    "executive": """You are a marketing analyst preparing an executive summary.

## Guidelines
1. Explore the data to answer the question
2. Lead with the bottom line - what should the executive know?
3. Provide 2-3 key metrics as evidence
4. End with a clear recommendation

## Format
**Bottom Line**: [One sentence answer]

**Key Metrics**:
- [Metric 1]
- [Metric 2]

**Recommendation**: [Action to take]

Keep it brief. Executives want answers, not analysis process."""
}

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


def execute_python(code: str, data_file: str) -> tuple[str, str | None]:
    """Run Python code. Returns (output, chart_path or None)."""
    chart_path = Path(__file__).parent / "output.png"
    if chart_path.exists():
        chart_path.unlink()

    # Determine data path - could be default or uploaded
    if Path(data_file).is_absolute():
        data_path = data_file
    else:
        data_path = str(DATA_DIR / data_file)

    wrapper = f'''
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Set style for better looking charts
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11

df = pd.read_csv("{data_path}")

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
                # Filter out common warnings
                stderr_lines = [
                    line for line in result.stderr.split('\n')
                    if line and 'warning' not in line.lower()
                ]
                if stderr_lines:
                    output += f"\n[stderr]: {chr(10).join(stderr_lines)}"

            chart = str(chart_path) if chart_path.exists() else None
            return output if output.strip() else "(no output)", chart

        except subprocess.TimeoutExpired:
            return "[Error]: Code execution timed out (30s limit)", None
        except Exception as e:
            return f"[Error]: {e}", None


def get_data_preview(data_file: str) -> str:
    """Generate a preview of the dataset."""
    try:
        if Path(data_file).is_absolute():
            df = pd.read_csv(data_file)
        else:
            df = pd.read_csv(DATA_DIR / data_file)

        rows, cols = df.shape
        date_range = ""
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            date_range = f" | {df['date'].min().strftime('%b %d')} - {df['date'].max().strftime('%b %d, %Y')}"

        campaigns = df['campaign_name'].nunique() if 'campaign_name' in df.columns else 0
        channels = df['channel'].nunique() if 'channel' in df.columns else 0

        preview = f"**Dataset loaded**: {rows} rows, {cols} columns{date_range}\n"
        if campaigns:
            preview += f"**Campaigns**: {campaigns} | **Channels**: {channels}\n"
        preview += f"**Columns**: {', '.join(df.columns)}"

        return preview
    except Exception as e:
        return f"Could not load data preview: {e}"


# Chat profiles for different analysis modes
@cl.set_chat_profiles
async def chat_profiles():
    return [
        cl.ChatProfile(
            name="Deep Analysis",
            markdown_description="Comprehensive analysis with charts and detailed recommendations",
            icon="https://api.iconify.design/carbon:analytics.svg",
        ),
        cl.ChatProfile(
            name="Quick Insights",
            markdown_description="Fast, direct answers with key metrics",
            icon="https://api.iconify.design/carbon:flash.svg",
        ),
        cl.ChatProfile(
            name="Executive Summary",
            markdown_description="Bottom-line findings for decision makers",
            icon="https://api.iconify.design/carbon:report.svg",
        ),
    ]


# Starter questions
@cl.set_starters
async def starters():
    return [
        cl.Starter(
            label="Best CPA campaign",
            message="Which campaign has the best cost per acquisition? Show me the top performers.",
            icon="https://api.iconify.design/carbon:trophy.svg",
        ),
        cl.Starter(
            label="Channel comparison",
            message="How does performance vary across channels? Compare CTR, conversion rate, and CPA.",
            icon="https://api.iconify.design/carbon:compare.svg",
        ),
        cl.Starter(
            label="Trend analysis",
            message="What trends do you see over time? Are there any patterns or anomalies?",
            icon="https://api.iconify.design/carbon:chart-line.svg",
        ),
        cl.Starter(
            label="Budget optimization",
            message="Where should we reallocate budget for maximum impact? Quantify the opportunity.",
            icon="https://api.iconify.design/carbon:currency-dollar.svg",
        ),
    ]


@cl.action_callback("reset_data")
async def reset_data(action):
    """Reset to the default dataset."""
    cl.user_session.set("data_file", DEFAULT_DATA_FILE)
    cl.user_session.set("messages", [])
    preview = get_data_preview(DEFAULT_DATA_FILE)
    await cl.Message(
        content=f"**Reset to default dataset**\n\n{preview}"
    ).send()


@cl.on_chat_start
async def start():
    # Get selected profile
    chat_profile = cl.user_session.get("chat_profile")

    # Map profile to prompt
    prompt_map = {
        "Deep Analysis": "deep",
        "Quick Insights": "quick",
        "Executive Summary": "executive",
    }
    prompt_key = prompt_map.get(chat_profile, "deep")

    cl.user_session.set("prompt_key", prompt_key)
    cl.user_session.set("data_file", DEFAULT_DATA_FILE)
    cl.user_session.set("messages", [])

    # Show data preview
    preview = get_data_preview(DEFAULT_DATA_FILE)

    mode_descriptions = {
        "deep": "comprehensive analysis with visualizations",
        "quick": "fast, direct answers",
        "executive": "bottom-line summaries",
    }

    actions = [
        cl.Action(name="reset_data", payload={}, label="Reset to Default Data"),
    ]

    await cl.Message(
        content=f"**{chat_profile or 'Deep Analysis'}** mode - {mode_descriptions.get(prompt_key, 'analysis')}\n\n{preview}\n\n---\nAsk a question or drag & drop a CSV file to analyze your own data.",
        actions=actions
    ).send()


@cl.on_message
async def main(message: cl.Message):
    messages = cl.user_session.get("messages", [])
    data_file = cl.user_session.get("data_file", DEFAULT_DATA_FILE)
    prompt_key = cl.user_session.get("prompt_key", "deep")

    # Handle file uploads
    if message.elements:
        for element in message.elements:
            if hasattr(element, 'path') and element.path and element.path.endswith('.csv'):
                # Validate the CSV
                try:
                    df = pd.read_csv(element.path)
                    cl.user_session.set("data_file", element.path)
                    data_file = element.path

                    preview = get_data_preview(element.path)
                    await cl.Message(
                        content=f"**New dataset loaded**\n\n{preview}\n\n---\nReady for analysis."
                    ).send()

                    # Reset conversation for new data
                    messages = []
                    cl.user_session.set("messages", messages)

                    # If there's no text with the file, just show the preview
                    if not message.content.strip():
                        return

                except Exception as e:
                    await cl.Message(
                        content=f"**Error loading CSV**: {e}\n\nPlease check the file format and try again."
                    ).send()
                    return

    # Add user message
    messages.append({"role": "user", "content": message.content})

    while True:
        msg = cl.Message(content="")
        await msg.send()

        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=PROMPTS[prompt_key],
                tools=tools,
                messages=messages
            ) as stream:
                for event in stream:
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_delta':
                            if hasattr(event.delta, 'text'):
                                await msg.stream_token(event.delta.text)

                final_message = stream.get_final_message()

        except anthropic.APIError as e:
            await msg.update()
            await cl.Message(content=f"**API Error**: {e.message}\n\nPlease try again.").send()
            return

        await msg.update()

        # Check if done
        if final_message.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": final_message.content})
            cl.user_session.set("messages", messages)
            return

        # Process tool calls
        tool_results = []
        for block in final_message.content:
            if block.type == "tool_use":
                goal = block.input.get("goal", "Analyzing...")
                code = block.input["code"]

                async with cl.Step(name=goal, type="tool") as step:
                    step.input = f"```python\n{code}\n```"
                    output, chart_path = execute_python(code, data_file)
                    step.output = output[:2000] + "..." if len(output) > 2000 else output

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
