# Data Analysis Agent

Code interpreter agent for marketing data analysis. The focus is on prompt engineering - iterating on system prompts to improve analysis quality.

## Setup

```bash
uv sync
```

## Usage

**CLI:**
```bash
uv run python agent.py
uv run python agent.py -p v3_analytical -q "Where should we reallocate budget?"
```

**Web UI (Chainlit):**
```bash
uv run chainlit run app.py
```
Opens at http://localhost:8000 - shows agent steps, code execution, and charts inline.

## Prompt Versions

Prompts live in `prompts/`. Each version represents a different approach:

- **v1_basic** - Minimal instructions, baseline
- **v2_structured** - Defined metrics, analysis steps
- **v3_analytical** - Analysis patterns, output structure

## Comparing Prompts

Run the same questions across prompt versions:

```bash
uv run python compare.py
uv run python compare.py -p v1_basic v3_analytical -q "Where should we shift budget?"
```

Results saved to `data/comparison_*.json`.

## Structure

```
agent.py      - Agent loop with code execution
prompts/      - System prompt versions
compare.py    - A/B comparison across prompts
data/         - Datasets and comparison results
```

## Adding Prompts

Create `prompts/v4_whatever.py`:

```python
SYSTEM_PROMPT = """..."""
```

Then test: `uv run python agent.py -p v4_whatever`
