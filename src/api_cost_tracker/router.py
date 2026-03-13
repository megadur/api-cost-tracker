import os
import anthropic
import google.generativeai as genai
import diskcache as dc
import logging
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".api_cost_tracker" / "cache"

# Gemini: $0 — covered by Google Pro subscription
# Claude: per-token billing
PRICING = {
    "gemini-2.0-flash":          {"input": 0.00,  "output": 0.00},
    "gemini-2.0-pro-exp":        {"input": 0.00,  "output": 0.00},
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00},
}

# Prefer Gemini (free) for low/medium; Claude only for high complexity
MODELS = {
    "low":    ("gemini",  "gemini-2.0-flash"),
    "medium": ("gemini",  "gemini-2.0-flash"),
    "high":   ("claude",  "claude-opus-4-6"),
}

@dataclass
class RequestRecord:
    timestamp:        str
    prompt_preview:   str
    complexity:       str
    provider:         str
    model_used:       str
    input_tokens:     int
    output_tokens:    int
    input_cost:       float
    output_cost:      float
    total_cost:       float
    cache_hit:        bool
    response_preview: str

def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    p  = PRICING.get(model, {"input": 0.0, "output": 0.0})
    ic = (input_tokens  / 1_000_000) * p["input"]
    oc = (output_tokens / 1_000_000) * p["output"]
    return {"input_cost": ic, "output_cost": oc, "total_cost": ic + oc}

def _classify(prompt: str) -> str:
    """Use Gemini Flash to classify complexity — free."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model    = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        f"Classify this task complexity. Reply with one word: low, medium, or high.\n\nTask: {prompt}"
    )
    return response.text.strip().lower()

def _call_gemini(prompt: str, model: str) -> tuple[str, int, int]:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    m        = genai.GenerativeModel(model)
    response = m.generate_content(prompt)
    # Gemini returns token counts in usage_metadata
    in_tok  = getattr(response.usage_metadata, "prompt_token_count",     0) or 0
    out_tok = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
    return response.text, in_tok, out_tok

def _call_claude(prompt: str, model: str) -> tuple[str, int, int]:
    client   = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text, response.usage.input_tokens, response.usage.output_tokens

def routed_call(prompt: str, ttl: int = 3600) -> RequestRecord:
    from .tracker import save_record  # avoid circular import

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = dc.Cache(str(CACHE_DIR))

    if prompt in cache:
        record = cache[prompt]
        record.cache_hit = True
        log.info(f"CACHE HIT | provider={record.provider} | model={record.model_used} | prompt={prompt[:80]!r}")
        save_record(record)
        return record

    complexity        = _classify(prompt)
    provider, model   = MODELS.get(complexity, ("claude", "claude-sonnet-4-6"))

    if provider == "gemini":
        text, in_tok, out_tok = _call_gemini(prompt, model)
    else:
        text, in_tok, out_tok = _call_claude(prompt, model)

    costs  = _calculate_cost(model, in_tok, out_tok)
    record = RequestRecord(
        timestamp        = datetime.now().isoformat(),
        prompt_preview   = prompt[:80],
        complexity       = complexity,
        provider         = provider,
        model_used       = model,
        input_tokens     = in_tok,
        output_tokens    = out_tok,
        input_cost       = costs["input_cost"],
        output_cost      = costs["output_cost"],
        total_cost       = costs["total_cost"],
        cache_hit        = False,
        response_preview = text[:80],
    )

    log.info(
        f"REQUEST | complexity={complexity} | provider={provider} | model={model} | "
        f"tokens={in_tok}in/{out_tok}out | cost=${costs['total_cost']:.6f}"
    )

    cache.set(prompt, record, expire=ttl)
    save_record(record)
    return record
