import anthropic
import diskcache as dc
import logging
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".api_cost_tracker" / "cache"

PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00},
}

MODELS = {
    "low":    "claude-haiku-4-5-20251001",
    "medium": "claude-sonnet-4-6",
    "high":   "claude-opus-4-6",
}

@dataclass
class RequestRecord:
    timestamp:        str
    prompt_preview:   str
    complexity:       str
    model_used:       str
    input_tokens:     int
    output_tokens:    int
    input_cost:       float
    output_cost:      float
    total_cost:       float
    cache_hit:        bool
    response_preview: str

def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    p  = PRICING[model]
    ic = (input_tokens  / 1_000_000) * p["input"]
    oc = (output_tokens / 1_000_000) * p["output"]
    return {"input_cost": ic, "output_cost": oc, "total_cost": ic + oc}

def _classify(client: anthropic.Anthropic, prompt: str) -> str:
    r = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"Classify this task complexity. Reply with one word: low, medium, or high.\n\nTask: {prompt}"
        }]
    )
    return r.content[0].text.strip().lower()

def routed_call(prompt: str, ttl: int = 3600) -> RequestRecord:
    from .tracker import save_record  # avoid circular import

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache  = dc.Cache(str(CACHE_DIR))
    client = anthropic.Anthropic()

    if prompt in cache:
        record = cache[prompt]
        record.cache_hit = True
        log.info(f"CACHE HIT | model={record.model_used} | prompt={prompt[:80]!r}")
        save_record(record)
        return record

    complexity = _classify(client, prompt)
    model      = MODELS.get(complexity, "claude-sonnet-4-6")

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    costs  = _calculate_cost(model, response.usage.input_tokens, response.usage.output_tokens)
    record = RequestRecord(
        timestamp        = datetime.now().isoformat(),
        prompt_preview   = prompt[:80],
        complexity       = complexity,
        model_used       = model,
        input_tokens     = response.usage.input_tokens,
        output_tokens    = response.usage.output_tokens,
        input_cost       = costs["input_cost"],
        output_cost      = costs["output_cost"],
        total_cost       = costs["total_cost"],
        cache_hit        = False,
        response_preview = response.content[0].text[:80],
    )

    log.info(
        f"REQUEST | complexity={complexity} | model={model} | "
        f"tokens={record.input_tokens}in/{record.output_tokens}out | "
        f"cost=${record.total_cost:.6f}"
    )

    cache.set(prompt, record, expire=ttl)
    save_record(record)
    return record
