import json
import os
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

import pytest

from personal_portfolio_manager.cli import main
from personal_portfolio_manager.data import load_plan
from personal_portfolio_manager.report import render_text, to_dict
from personal_portfolio_manager.strategies import allocate

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.mark.parametrize("name", ["first-month.json", "later-month.json"])
def test_examples_load_and_conserve_cash(name):
    p = allocate(load_plan(EXAMPLES / name))
    assert p.conserves_cash()
    assert p.breaches_after == ()


def test_first_month_goes_to_emergency_fund():
    p = allocate(load_plan(EXAMPLES / "first-month.json"))
    assert p.to_emergency == D(20000) and p.purchases == ()


def test_json_output_is_serializable_and_exact(capsys):
    assert main(["allocate", str(EXAMPLES / "later-month.json"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["review_required"] is True
    assert data["status"] == "awaiting_review"
    total = sum(D(x["cost"]) for x in data["purchases"])
    assert str(total) == data["purchased_total"]


def test_text_report_mentions_pending_settlement():
    text = render_text(allocate(load_plan(EXAMPLES / "later-month.json")))
    assert "takasta" in text and "emir değildir" in text
    assert "Yatırım tavsiyesi değildir" in text


def test_invalid_file_exit_code(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"as_of": "2026-11-11"}', encoding="utf-8")
    assert main(["allocate", str(bad)]) == 2
    assert "Geçersiz plan" in capsys.readouterr().err


def test_missing_file_exit_code(tmp_path):
    assert main(["allocate", str(tmp_path / "nope.json")]) == 2


def test_stale_plan_exit_code(tmp_path):
    data = json.loads((EXAMPLES / "later-month.json").read_text(encoding="utf-8"))
    data["as_of"] = "2026-12-01"
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["allocate", str(path)]) == 3


def test_result_independent_of_hash_seed():
    outputs = set()
    for seed in ("0", "1", "42"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run(
            [sys.executable, "-m", "personal_portfolio_manager", "allocate",
             str(EXAMPLES / "later-month.json"), "--json"],
            capture_output=True, check=True, env=env,
        ).stdout
        outputs.add(out)
    assert len(outputs) == 1


def test_to_dict_has_no_decimal_objects():
    data = to_dict(allocate(load_plan(EXAMPLES / "later-month.json")))
    json.dumps(data)  # raises on Decimal/date/Enum leftovers
