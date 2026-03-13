from dataclasses import asdict
from .db import get_conn, init_db
from .router import RequestRecord

init_db()

def save_record(record: RequestRecord):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO requests (
                timestamp, prompt_preview, complexity, provider, model_used,
                input_tokens, output_tokens, input_cost, output_cost,
                total_cost, cache_hit, response_preview
            ) VALUES (
                :timestamp, :prompt_preview, :complexity, :provider, :model_used,
                :input_tokens, :output_tokens, :input_cost, :output_cost,
                :total_cost, :cache_hit, :response_preview
            )
        """, asdict(record))

def get_summary(since: str = None) -> dict:
    where  = "WHERE timestamp >= :since" if since else ""
    params = {"since": since}
    with get_conn() as conn:
        totals   = conn.execute(f"""
            SELECT COUNT(*) AS requests, SUM(total_cost) AS cost,
                   SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens,
                   SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits
            FROM requests {where}
        """, params).fetchone()
        by_model = conn.execute(f"""
            SELECT provider, model_used, COUNT(*) AS calls, SUM(total_cost) AS cost,
                   AVG(total_cost) AS avg_cost,
                   SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens
            FROM requests {where} GROUP BY model_used ORDER BY cost DESC
        """, params).fetchall()
        by_day   = conn.execute(f"""
            SELECT DATE(timestamp) AS day, COUNT(*) AS calls, SUM(total_cost) AS cost,
                   SUM(cache_hit) AS cache_hits
            FROM requests {where} GROUP BY day ORDER BY day DESC LIMIT 30
        """, params).fetchall()
    return {
        "totals":   dict(totals),
        "by_model": [dict(r) for r in by_model],
        "by_day":   [dict(r) for r in by_day],
    }

class CostTracker:
    def __init__(self): self.records: list[RequestRecord] = []
    def add(self, r: RequestRecord): self.records.append(r)

    @property
    def total_cost(self): return sum(r.total_cost for r in self.records)

    def summary(self):
        print(f"\nSession: {len(self.records)} requests | ${self.total_cost:.6f} total")

def print_summary(since: str = None):
    s = get_summary(since)
    t = s["totals"]
    print(f"\n{'='*55}")
    print(f"  LIFETIME SUMMARY")
    print(f"{'='*55}")
    print(f"  Requests   : {t['requests']}")
    print(f"  Total cost : ${t['cost'] or 0:.6f}")
    print(f"  Tokens     : {t['input_tokens'] or 0} in / {t['output_tokens'] or 0} out")
    print(f"  Cache hits : {t['cache_hits']}")
    print(f"\n  By provider/model:")
    for m in s["by_model"]:
        tag = "(subscription)" if m["provider"] == "gemini" else f"${m['cost']:.6f}"
        print(f"    [{m['provider']:<6}] {m['model_used']:<32} {tag} ({m['calls']} calls, {m['input_tokens']}in/{m['output_tokens']}out tokens)")
    print(f"{'='*55}\n")
