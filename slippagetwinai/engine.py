"""Small transparent ridge model and chronological evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .core import Config, Fill, TwinError

NAMES = ["intercept", "half_spread_bps", "volatility_bps", "sqrt_participation", "log1p_quantity"]


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector); aug = [matrix[i][:] + [vector[i]] for i in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(aug[row][column]))
        if abs(aug[pivot][column]) < 1e-12: raise TwinError("calibration matrix is singular; increase ridge or vary the data")
        aug[column], aug[pivot] = aug[pivot], aug[column]
        scale = aug[column][column]; aug[column] = [x / scale for x in aug[column]]
        for row in range(n):
            if row == column: continue
            factor = aug[row][column]; aug[row] = [a - factor * b for a, b in zip(aug[row], aug[column])]
    return [aug[i][-1] for i in range(n)]


def fit(rows: list[Fill], ridge: float) -> list[float]:
    size = len(NAMES); xtx = [[0.0] * size for _ in range(size)]; xty = [0.0] * size
    for fill in rows:
        x, y = fill.features, fill.target_bps
        for i in range(size):
            xty[i] += x[i] * y
            for j in range(size): xtx[i][j] += x[i] * x[j]
    for i in range(1, size): xtx[i][i] += ridge
    return solve(xtx, xty)


def predict(fill: Fill, coefficients: list[float]) -> float:
    return sum(a * b for a, b in zip(fill.features, coefficients))


def metrics(rows: list[Fill], coefficients: list[float]) -> dict[str, Any]:
    errors = [predict(row, coefficients) - row.target_bps for row in rows]
    return {
        "count": len(rows),
        "mae_bps": round(sum(abs(x) for x in errors) / len(errors), 8),
        "rmse_bps": round(math.sqrt(sum(x*x for x in errors) / len(errors)), 8),
        "bias_bps": round(sum(errors) / len(errors), 8),
        "actual_mean_bps": round(sum(x.target_bps for x in rows) / len(rows), 8),
        "predicted_mean_bps": round(sum(predict(x, coefficients) for x in rows) / len(rows), 8),
    }


def run(config: Config, fills: list[Fill]) -> dict[str, Any]:
    test_start = config.calibration_count + config.embargo_count
    if test_start >= len(fills): raise TwinError("no chronological holdout remains after calibration and embargo")
    calibration, test = fills[:config.calibration_count], fills[test_start:]
    coefficients = fit(calibration, config.ridge)
    bounds = {name: {"min": round(min(row.features[i] for row in calibration), 8), "max": round(max(row.features[i] for row in calibration), 8)} for i, name in enumerate(NAMES[1:], start=1)}
    outside = sum(any(row.features[i] < bounds[name]["min"] or row.features[i] > bounds[name]["max"] for i, name in enumerate(NAMES[1:], start=1)) for row in test)
    report = {
        "schema":"slippagetwinai/report-1",
        "split":{"calibration":{"start":calibration[0].timestamp,"end":calibration[-1].timestamp,"count":len(calibration)},"embargo":{"count":config.embargo_count},"test":{"start":test[0].timestamp,"end":test[-1].timestamp,"count":len(test)}},
        "model":{"kind":"ridge_linear","ridge":config.ridge,"feature_contract":"arrival_time_only","coefficients_bps":{name:round(value,10) for name,value in zip(NAMES,coefficients)},"calibration_bounds":bounds},
        "calibration_metrics":metrics(calibration, coefficients),
        "test_metrics":metrics(test, coefficients),
        "test_rows_outside_calibration_bounds":outside,
        "claims":"historical_execution_cost_measurement_only",
    }
    report["report_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return report
