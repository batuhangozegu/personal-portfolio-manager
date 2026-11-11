"""Command line: ``ppm allocate plan.json [--json]``.

Exit codes: 0 proposal ready for review, 2 invalid input, 3 blocked by stale data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .data.loader import load_plan
from .report import render_text, to_dict
from .strategies.allocation import BLOCKED, allocate


def _utf8_stdout() -> None:
    # Piped output on Windows defaults to a legacy code page without '₺'.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser(prog="ppm", description="Kural tabanlı katkı dağıtım önerisi.")
    sub = parser.add_subparsers(dest="command", required=True)
    alloc = sub.add_parser("allocate", help="Bir plan dosyası için katkı önerisi üret.")
    alloc.add_argument("plan", type=Path, help="Plan JSON dosyası")
    alloc.add_argument("--json", action="store_true", help="Metin yerine JSON çıktı ver")
    args = parser.parse_args(argv)

    try:
        plan = load_plan(args.plan)
    except FileNotFoundError:
        print(f"Dosya bulunamadı: {args.plan}", file=sys.stderr)
        return 2
    except (ValidationError, ValueError) as exc:
        print(f"Geçersiz plan dosyası: {exc}", file=sys.stderr)
        return 2

    proposal = allocate(plan)
    if args.json:
        print(json.dumps(to_dict(proposal), ensure_ascii=False, indent=2))
    else:
        print(render_text(proposal))
    return 3 if proposal.status == BLOCKED else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
