# api-cost-tracker

Track, cache, and analyze Claude and Gemini API costs from the terminal.

## Features

- **Model routing** — automatically classifies task complexity and routes to the cheapest model
- **Caching** — skips API calls for repeated prompts (zero cost)
- **Cost tracking** — logs token usage and cost per request to SQLite
- **CLI** — query cost history from the terminal
- **Gemini support** — tracks token usage for Gemini (free via Google subscription)

## Routing strategy

| Complexity | Provider | Model | Cost |
|---|---|---|---|
| Low | Gemini | gemini-2.0-flash | $0 (subscription) |
| Medium | Gemini | gemini-2.0-flash | $0 (subscription) |
| High | Claude | claude-opus-4-6 | Per token |

## Installation

```bash
git clone https://github.com/megadur/api-cost-tracker.git
cd api-cost-tracker
pip install -e .
```

## Setup

```bash
export ANTHROPIC_API_KEY="your-claude-api-key"
export GEMINI_API_KEY="your-gemini-api-key"   # free at https://aistudio.google.com
```

Add both to `~/.bashrc` to persist across sessions.

## Usage

```python
from api_cost_tracker import routed_call

record = routed_call("Summarize this article: ...")
print(record.model_used)    # gemini-2.0-flash
print(record.total_cost)    # 0.0
print(record.input_tokens)  # 142
```

## CLI

```bash
# overall summary
costs summary

# last 7 days
costs summary --period 7d

# daily breakdown
costs daily --period 30d

# most expensive requests
costs top --limit 5

# breakdown by provider/model
costs models --period 1m

# export to CSV
costs export > costs.csv

# clear all records
costs clear
```

## Sample output

```
==================================================
  SUMMARY (last 7d)
==================================================
  Requests   : 42
  Total cost : $0.142100
  Tokens     : 18420 in / 9310 out
  Cache hits : 15

  By model:
    [gemini] gemini-2.0-flash           (subscription) (28 calls)
    [claude] claude-opus-4-6            $0.142100      (4 calls)
==================================================
```

## Data storage

All data is stored locally at `~/.api_cost_tracker/`:

```
~/.api_cost_tracker/
├── costs.db    # SQLite database
└── cache/      # diskcache response cache
```

## Development

```bash
pip install -e ".[dev]"
pytest
pytest --cov=api_cost_tracker --cov-report=term-missing
```

## Pricing reference

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| gemini-2.0-flash | $0.00 (subscription) | $0.00 (subscription) |
| claude-haiku-4-5 | $0.80 | $4.00 |
| claude-sonnet-4-6 | $3.00 | $15.00 |
| claude-opus-4-6 | $15.00 | $75.00 |
