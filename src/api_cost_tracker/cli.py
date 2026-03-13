import argparse
from datetime import datetime, timedelta
from .db import get_conn, init_db
from .tracker import get_summary

init_db()

def parse_period(period: str) -> str:
    unit, value = period[-1], int(period[:-1])
    delta = {
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
        "m": timedelta(days=value * 30),
    }.get(unit)
    if not delta:
        raise ValueError(f"Invalid period '{period}'. Use: 7d, 2w, 1m")
    return (datetime.now() - delta).isoformat()

def fmt(cost): return f"${cost:.6f}"

def cmd_summary(args):
    since = parse_period(args.period) if args.period else None
    s     = get_summary(since)
    t     = s["totals"]
    label = f"last {args.period}" if args.period else "all time"
    print(f"\n{'='*50}\n  SUMMARY ({label})\n{'='*50}")
    print(f"  Requests   : {t['requests']}")
    print(f"  Total cost : {fmt(t['cost'] or 0)}")
    print(f"  Tokens     : {t['input_tokens'] or 0} in / {t['output_tokens'] or 0} out")
    print(f"  Cache hits : {t['cache_hits']}\n  By model:")
    for m in s["by_model"]:
        print(f"    {m['model_used']:<38} {fmt(m['cost'])} ({m['calls']} calls)")
    print(f"{'='*50}\n")

def cmd_daily(args):
    since = parse_period(args.period)
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DATE(timestamp) AS day, COUNT(*) AS calls,
                   SUM(total_cost) AS cost, SUM(cache_hit) AS cache_hits
            FROM requests WHERE timestamp >= :since
            GROUP BY day ORDER BY day DESC
        """, {"since": since}).fetchall()
    print(f"\n  {'DATE':<12} {'CALLS':>6} {'CACHE':>6} {'COST':>12}")
    print(f"  {'-'*38}")
    for r in rows:
        print(f"  {r['day']:<12} {r['calls']:>6} {r['cache_hits']:>6} {fmt(r['cost']):>12}")
    print()

def cmd_top(args):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT prompt_preview, model_used, total_cost, timestamp
            FROM requests WHERE cache_hit = 0
            ORDER BY total_cost DESC LIMIT :limit
        """, {"limit": args.limit}).fetchall()
    print(f"\n  Top {args.limit} most expensive requests:\n")
    for i, r in enumerate(rows, 1):
        print(f"  {i}. {fmt(r['total_cost'])} | {r['model_used']}")
        print(f"     {r['timestamp'][:19]}  {r['prompt_preview']!r}")
    print()

def cmd_models(args):
    since = parse_period(args.period) if args.period else None
    s     = get_summary(since)
    label = f"last {args.period}" if args.period else "all time"
    print(f"\n  Model breakdown ({label}):\n")
    print(f"  {'MODEL':<38} {'CALLS':>6} {'AVG':>10} {'TOTAL':>12}")
    print(f"  {'-'*68}")
    for m in s["by_model"]:
        print(f"  {m['model_used']:<38} {m['calls']:>6} {fmt(m['avg_cost']):>10} {fmt(m['cost']):>12}")
    print()

def cmd_export(args):
    import csv, sys
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM requests ORDER BY timestamp DESC").fetchall()
    if not rows:
        print("No records found.")
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows([dict(r) for r in rows])

def cmd_clear(args):
    confirm = input("Delete all records? Type 'yes' to confirm: ")
    if confirm.strip().lower() == "yes":
        with get_conn() as conn:
            conn.execute("DELETE FROM requests")
        print("All records deleted.")
    else:
        print("Cancelled.")

def main():
    parser = argparse.ArgumentParser(prog="costs", description="Query API cost history")
    sub    = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("summary", help="Overall cost summary")
    p.add_argument("--period", metavar="PERIOD", help="7d, 2w, 1m (default: all time)")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("daily", help="Cost breakdown by day")
    p.add_argument("--period", metavar="PERIOD", default="30d")
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("top", help="Most expensive requests")
    p.add_argument("--limit", type=int, default=10, metavar="N")
    p.set_defaults(func=cmd_top)

    p = sub.add_parser("models", help="Breakdown by model")
    p.add_argument("--period", metavar="PERIOD", help="7d, 2w, 1m (default: all time)")
    p.set_defaults(func=cmd_models)

    p = sub.add_parser("export", help="Export all records to CSV")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("clear", help="Delete all records")
    p.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
