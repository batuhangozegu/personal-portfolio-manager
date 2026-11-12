"""Point-in-time store: nothing published after the query moment may be visible."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from personal_portfolio_manager.data.pit import (
    DuplicateObservationError,
    Observation,
    PointInTimeStore,
)

IST = timezone(timedelta(hours=3))
FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "pit-fixture.jsonl"
FY2024 = date(2024, 12, 31)


def at(y: int, m: int, d: int, hh: int = 0, mm: int = 0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=IST)


def obs(**kw) -> Observation:
    base = dict(entity="SYNTH", field="net_income", period=FY2024, value=Decimal("1"),
                published_at=at(2025, 3, 10, 18, 30), source="synthetic")
    base.update(kw)
    return Observation(**base)


@pytest.fixture
def store() -> PointInTimeStore:
    return PointInTimeStore.load_jsonl(FIXTURE)


def test_fixture_loads(store):
    assert len(store) == 5


def test_not_visible_before_publication(store):
    view = store.as_of(at(2025, 3, 10, 18, 29))
    assert view.get("SYNTH", "net_income", FY2024) is None
    assert view.series("SYNTH", "net_income") == []
    assert view.latest("SYNTH", "net_income") is None


def test_visible_exactly_at_publication(store):
    found = store.as_of(at(2025, 3, 10, 18, 30)).get("SYNTH", "net_income", FY2024)
    assert found is not None and found.value == Decimal("1000")


def test_restatement_replaces_only_after_its_publication(store):
    before = store.as_of(at(2025, 5, 1)).get("SYNTH", "net_income", FY2024)
    after = store.as_of(at(2025, 5, 3)).get("SYNTH", "net_income", FY2024)
    assert before.value == Decimal("1000")
    assert after.value == Decimal("900")
    assert after.reference == "synthetic-fy2024-restated"


def test_series_and_latest(store):
    view = store.as_of(at(2025, 6, 1))
    assert [o.value for o in view.series("SYNTH", "net_income")] == [Decimal("900"), Decimal("250")]
    assert view.latest("SYNTH", "net_income").period == date(2025, 3, 31)


def test_unknown_series_is_empty_not_error(store):
    view = store.as_of(at(2026, 1, 1))
    assert view.series("NOPE", "close") == []
    assert view.latest("NOPE", "close") is None


def test_cpi_respects_publication_lag(store):
    april = date(2025, 4, 30)
    assert store.as_of(at(2025, 5, 4, 23, 59)).get("TUFE", "index", april) is None
    assert store.as_of(at(2025, 5, 5)).get("TUFE", "index", april) is not None


def test_timezones_compare_by_instant(store):
    # 18:30 Istanbul == 15:30 UTC: visible at 15:30 UTC, not at 15:29 UTC.
    utc = timezone.utc
    assert store.as_of(datetime(2025, 3, 10, 15, 29, tzinfo=utc)).get("SYNTH", "net_income", FY2024) is None
    assert store.as_of(datetime(2025, 3, 10, 15, 30, tzinfo=utc)).get("SYNTH", "net_income", FY2024) is not None


def test_naive_datetimes_rejected():
    with pytest.raises(ValidationError):
        obs(published_at=datetime(2025, 3, 10, 18, 30))
    with pytest.raises(ValueError):
        PointInTimeStore().as_of(datetime(2025, 1, 1))


def test_publication_before_period_rejected():
    with pytest.raises(ValidationError):
        obs(period=date(2025, 3, 31), published_at=at(2025, 3, 30))


def test_identical_record_is_idempotent_conflicting_one_rejected():
    store = PointInTimeStore([obs()])
    store.add(obs())
    assert len(store) == 1
    with pytest.raises(DuplicateObservationError):
        store.add(obs(value=Decimal("2")))


def test_round_trip_keeps_decimal_precision(tmp_path):
    original = PointInTimeStore([obs(value=Decimal("0.1000000000000000055511151231"))])
    path = tmp_path / "nested" / "store.jsonl"
    original.save_jsonl(path)
    loaded = PointInTimeStore.load_jsonl(path)
    assert list(loaded) == list(original)


def test_load_reports_bad_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"entity": "X"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.jsonl:1"):
        PointInTimeStore.load_jsonl(path)
