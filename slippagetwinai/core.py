"""Strict arrival-time feature and fill parsing."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TwinError(ValueError):
    pass


@dataclass(frozen=True)
class Fill:
    timestamp: str
    side: str
    quantity: float
    arrival_mid: float
    execution_price: float
    spread_bps: float
    volatility_bps: float
    participation_rate: float

    @property
    def target_bps(self) -> float:
        sign = 1.0 if self.side == "buy" else -1.0
        return sign * (self.execution_price - self.arrival_mid) / self.arrival_mid * 10000.0

    @property
    def features(self) -> tuple[float, ...]:
        return (1.0, self.spread_bps / 2.0, self.volatility_bps, math.sqrt(self.participation_rate), math.log1p(self.quantity))


@dataclass(frozen=True)
class Config:
    calibration_count: int
    embargo_count: int
    ridge: float


def finite(value: Any, label: str, *, positive: bool = False) -> float:
    try: result = float(value)
    except (TypeError, ValueError) as exc: raise TwinError(f"{label} must be numeric") from exc
    if not math.isfinite(result) or (positive and result <= 0): raise TwinError(f"{label} must be finite{' and positive' if positive else ''}")
    return result


def parse_config(raw: Any) -> Config:
    if not isinstance(raw, dict) or set(raw) != {"calibration_count", "embargo_count", "ridge"}: raise TwinError("config fields are incomplete or unexpected")
    calibration, embargo = raw["calibration_count"], raw["embargo_count"]
    if type(calibration) is not int or calibration < 5: raise TwinError("calibration_count must be at least 5")
    if type(embargo) is not int or embargo < 0: raise TwinError("embargo_count must be non-negative")
    ridge = finite(raw["ridge"], "ridge")
    if ridge < 0 or ridge > 1000: raise TwinError("ridge must be from 0 to 1000")
    return Config(calibration, embargo, ridge)


def load_fills(path: str) -> list[Fill]:
    fields = ["timestamp", "side", "quantity", "arrival_mid", "execution_price", "spread_bps", "volatility_bps", "participation_rate"]
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields: raise TwinError("CSV header does not match the arrival-feature contract")
        rows = list(reader)
    fills = []; previous: datetime | None = None
    for row in rows:
        stamp = row["timestamp"]
        if not stamp.endswith("Z"): raise TwinError("timestamp must be canonical UTC")
        try: current = datetime.fromisoformat(stamp[:-1] + "+00:00")
        except ValueError as exc: raise TwinError("timestamp must be ISO-8601 UTC") from exc
        if current.tzinfo != timezone.utc or current.isoformat().replace("+00:00", "Z") != stamp: raise TwinError("timestamp must be canonical UTC")
        if previous is not None and current <= previous: raise TwinError("timestamps must strictly increase")
        if row["side"] not in {"buy", "sell"}: raise TwinError("side must be buy or sell")
        values = [finite(row[x], x, positive=x in {"quantity", "arrival_mid", "execution_price"}) for x in fields[2:]]
        quantity, arrival, execution, spread, volatility, participation = values
        if spread < 0 or volatility < 0 or not 0 <= participation <= 1: raise TwinError("arrival features have invalid bounds")
        fills.append(Fill(stamp, row["side"], quantity, arrival, execution, spread, volatility, participation)); previous = current
    if not fills: raise TwinError("CSV must contain fills")
    return fills
