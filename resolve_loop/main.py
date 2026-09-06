"""CLI entrypoint for running the ResolveLoop MVP."""
import sys
from resolve_loop.engine import run_demo_loop

def main():
    out = run_demo_loop()
    print("ResolveLoop MVP Run Summary:")
    if isinstance(out, dict) and "error" in out:
        print(f"Error: {out['error']}")
        sys.exit(1)
    for idx, r in enumerate(out.get("results", []), 1):
        print(f"Case {idx}: {r['case']['id']} - Score: {r['score']}")
    print("Benchmark:", out.get("benchmark"))

if __name__ == "__main__":
    main()
