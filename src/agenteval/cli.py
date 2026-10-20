"""Command-line interface. The offline demo never reads model credentials."""
import argparse
import asyncio
from importlib.resources import files
import json
import os
from pathlib import Path
import sys
from .api import evaluate
from .render import render_html


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agenteval", description="Trace → executable checks → inspectable evidence")
    subs = parser.add_subparsers(dest="command", required=True)
    demo = subs.add_parser("demo", help="Run authored examples locally; no API key or model needed")
    demo.add_argument("--out", type=Path, default=Path("runs/demo"))
    run = subs.add_parser("run", help="Evaluate your traces with trusted rules and/or model judges")
    run.add_argument("input", type=Path)
    run.add_argument("--rules", type=Path)
    run.add_argument("--evaluators", type=Path)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--concurrency", type=int, default=4)
    run.add_argument("--n-runs", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError("Output already exists. Choose a new --out directory to preserve prior runs.")
        if args.command == "demo":
            data = files("agenteval").joinpath("demo")
            result = asyncio.run(evaluate(json.loads(data.joinpath("traces.json").read_text(encoding="utf-8")),
                rules_yaml=data.joinpath("rules.yaml").read_text(encoding="utf-8")))
            result["demo"] = True
        else:
            options = {"api_key": os.environ.get("AGENTEVAL_API_KEY", ""),
                "base_url": os.environ.get("AGENTEVAL_BASE_URL", ""), "model": os.environ.get("AGENTEVAL_MODEL", "")}
            result = asyncio.run(evaluate(json.loads(args.input.read_text(encoding="utf-8")),
                rules_yaml=args.rules.read_text(encoding="utf-8") if args.rules else "",
                evaluators_yaml=args.evaluators.read_text(encoding="utf-8") if args.evaluators else "",
                model_options=options, concurrency=args.concurrency, n_runs=args.n_runs))
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.out / "report.html").write_text(render_html(result), encoding="utf-8")
        print(json.dumps(result["summary"]))
        print(f"Report: {(args.out / 'report.html').resolve()}")
        return 2 if result["summary"]["error"] else 0
    except (ValueError, OSError) as exc:
        # Input errors are useful; provider exception text never reaches reports.
        print(f"AgentEval: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
