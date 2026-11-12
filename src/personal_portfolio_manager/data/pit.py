"""Point-in-time store for dated source records.

Every observation says *what period* a value describes (``period``) and *when*
it became publicly known (``published_at``). Queries are always made "as of" a
moment, and only observations published at or before that moment are visible.
This keeps backtests from seeing statements, prices or CPI prints before they
were actually available (docs/decisions.md section 11).

Restatements are new observations for the same (entity, field, period) with a
later ``published_at``; a view returns the latest version known at its moment.

Local datasets are stored as JSON Lines under the git-ignored ``/data/``
directory; only synthetic fixtures are committed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Key = tuple[str, str]  # (entity, field)


class Observation(BaseModel):
    """One published value, e.g. a company's net income for a fiscal period."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entity: str = Field(min_length=1)  # e.g. a ticker, "USDTRY", "TUFE"
    field: str = Field(min_length=1)  # e.g. "net_income", "close"
    period: date  # date the value refers to: period end, price date, CPI month end
    value: Decimal
    published_at: datetime  # timezone-aware moment the value became public
    source: str = Field(min_length=1)  # e.g. "kap", "yahoo", "evds", "synthetic"
    reference: str | None = None  # e.g. a KAP disclosure id or URL

    @field_validator("published_at")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        return v

    @model_validator(mode="after")
    def _not_before_period(self) -> Observation:
        if self.published_at.date() < self.period:
            raise ValueError(
                f"{self.entity}/{self.field}: published {self.published_at.date()} "
                f"before its period {self.period}"
            )
        return self


class DuplicateObservationError(ValueError):
    """Same (entity, field, period, published_at) added twice with different data."""


class PointInTimeStore:
    """In-memory collection of observations with as-of queries."""

    def __init__(self, observations: Iterable[Observation] = ()) -> None:
        self._by_key: dict[Key, list[Observation]] = defaultdict(list)
        self._seen: dict[tuple[str, str, date, datetime], Observation] = {}
        for obs in observations:
            self.add(obs)

    def add(self, obs: Observation) -> None:
        ident = (obs.entity, obs.field, obs.period, obs.published_at)
        existing = self._seen.get(ident)
        if existing is not None:
            if existing == obs:
                return  # re-ingesting the same record is harmless
            raise DuplicateObservationError(
                f"conflicting records for {obs.entity}/{obs.field} {obs.period} "
                f"published {obs.published_at.isoformat()}"
            )
        self._seen[ident] = obs
        self._by_key[(obs.entity, obs.field)].append(obs)

    def __len__(self) -> int:
        return len(self._seen)

    def __iter__(self) -> Iterator[Observation]:
        return iter(sorted(self._seen.values(), key=_sort_key))

    def as_of(self, moment: datetime) -> AsOfView:
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("as_of moment must be timezone-aware")
        return AsOfView(self, moment)

    def _versions(self, entity: str, field: str) -> list[Observation]:
        return self._by_key.get((entity, field), [])

    # --- persistence -------------------------------------------------------

    def save_jsonl(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for obs in self:
                fh.write(obs.model_dump_json() + "\n")

    @classmethod
    def load_jsonl(cls, path: str | Path) -> PointInTimeStore:
        store = cls()
        with Path(path).open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line, parse_float=Decimal)
                    store.add(Observation.model_validate(raw))
                except (ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"{path}:{lineno}: {exc}") from exc
        return store


class AsOfView:
    """What was publicly known at ``moment``. Nothing published later is visible."""

    def __init__(self, store: PointInTimeStore, moment: datetime) -> None:
        self._store = store
        self.moment = moment

    def _known(self, entity: str, field: str) -> dict[date, Observation]:
        latest: dict[date, Observation] = {}
        for obs in self._store._versions(entity, field):
            if obs.published_at > self.moment:
                continue
            cur = latest.get(obs.period)
            if cur is None or obs.published_at > cur.published_at:
                latest[obs.period] = obs
        return latest

    def get(self, entity: str, field: str, period: date) -> Observation | None:
        """Latest known version for one period, or ``None`` if not yet published."""
        return self._known(entity, field).get(period)

    def series(self, entity: str, field: str) -> list[Observation]:
        """Latest known version of every published period, oldest period first."""
        known = self._known(entity, field)
        return [known[p] for p in sorted(known)]

    def latest(self, entity: str, field: str) -> Observation | None:
        """Most recent period known at this moment, or ``None``."""
        known = self._known(entity, field)
        return known[max(known)] if known else None


def _sort_key(obs: Observation) -> tuple[str, str, date, datetime]:
    return (obs.entity, obs.field, obs.period, obs.published_at)
