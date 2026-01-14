# Data Analyst Agent

A CodeAct demonstration for marketing data analysis.

## What is CodeAct?

CodeAct is a pattern where LLMs generate and execute code rather than producing text responses directly. For data analysis, this means:

- Metrics are computed, not hallucinated
- Results are grounded in actual data
- The reasoning process is auditable (you see the code)

This project explores how system prompt design affects CodeAct agent behavior.

## Quick Start

```bash
uv sync
uv run python -m chainlit run app.py
```

Opens at `localhost:8000`. Select an analysis mode, pick a starter question or ask your own.

## Structure

```
app.py        Web UI (Chainlit) with chat profiles and file upload
agent.py      CLI agent with interactive mode
compare.py    A/B test prompts on the same questions
prompts/      System prompt versions (v1-v4)
data/         Sample marketing dataset
```

## Prompt Versions

Each prompt takes a different approach to guiding the agent:

| Version | Approach |
|---------|----------|
| v1_basic | Minimal - baseline |
| v2_structured | Metric definitions, analysis steps |
| v3_analytical | Analysis patterns (comparison, trend, decomposition) |
| v4_professional | Structured workflow with output format |

The web UI uses three modes (Quick/Deep/Executive) derived from these.

## CLI Usage

```bash
# Interactive
uv run python agent.py

# Single question with specific prompt
uv run python agent.py -p v3_analytical -q "Which campaign has the best CPA?"

# Compare prompts
uv run python compare.py -p v1_basic v4_professional
```

## Adding Prompts

Create `prompts/v5_whatever.py`:

```python
SYSTEM_PROMPT = """Your prompt here"""
```

Test with `uv run python agent.py -p v5_whatever`

## License

MIT
