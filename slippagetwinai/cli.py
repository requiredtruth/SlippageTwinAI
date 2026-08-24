from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import TwinError, load_fills, parse_config
from .engine import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slippagetwinai", description="Chronological empirical slippage twin")
    parser.add_argument("config"); parser.add_argument("fills"); parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        report = run(parse_config(json.loads(Path(args.config).read_text(encoding="utf-8"))), load_fills(args.fills))
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output: Path(args.output).write_text(rendered, encoding="utf-8")
        else: print(rendered, end="")
    except (OSError, json.JSONDecodeError, TwinError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2
    return 0
