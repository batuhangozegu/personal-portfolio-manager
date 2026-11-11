"""Load plan JSON files without losing decimal precision."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from .models import Plan


def parse_plan(text: str) -> Plan:
    """Parse JSON text. Numbers become ``Decimal`` directly, never ``float``."""
    raw = json.loads(text, parse_float=Decimal)
    return Plan.model_validate(raw)


def load_plan(path: str | Path) -> Plan:
    return parse_plan(Path(path).read_text(encoding="utf-8"))
