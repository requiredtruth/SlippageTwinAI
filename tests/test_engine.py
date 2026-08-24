import copy
import json
import tempfile
import unittest
from pathlib import Path

from slippagetwinai.core import TwinError, load_fills, parse_config
from slippagetwinai.engine import fit, predict, run

DATA = Path(__file__).parents[1] / "slippagetwinai" / "data"


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((DATA/"demo_config.json").read_text())
        self.fills = load_fills(str(DATA/"demo_fills.csv"))

    def test_chronological_split_and_metrics(self):
        report = run(parse_config(self.raw), self.fills)
        self.assertEqual(report["split"]["calibration"]["count"], 12)
        self.assertEqual(report["split"]["embargo"]["count"], 2)
        self.assertEqual(report["split"]["test"]["count"], 6)
        self.assertLess(report["split"]["calibration"]["end"], report["split"]["test"]["start"])
        self.assertEqual(report["model"]["feature_contract"], "arrival_time_only")

    def test_target_sign_is_adverse_for_buy_and_sell(self):
        self.assertGreater(self.fills[0].target_bps, 0)
        self.assertGreater(self.fills[1].target_bps, 0)

    def test_model_is_deterministic(self):
        config = parse_config(self.raw)
        self.assertEqual(run(config, self.fills), run(config, copy.deepcopy(self.fills)))

    def test_prediction_uses_only_arrival_features(self):
        coefficients = fit(self.fills[:12], 0.1)
        original = predict(self.fills[0], coefficients)
        changed = type(self.fills[0])(**{**self.fills[0].__dict__, "execution_price": 999})
        self.assertEqual(original, predict(changed, coefficients))

    def test_rejects_no_holdout(self):
        self.raw["calibration_count"] = 19; self.raw["embargo_count"] = 1
        with self.assertRaisesRegex(TwinError, "no chronological holdout"):
            run(parse_config(self.raw), self.fills)

    def test_rejects_bad_participation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = (DATA/"demo_fills.csv").read_text().replace(",0.01\n", ",1.01\n", 1)
            path = Path(tmp)/"bad.csv"; path.write_text(source)
            with self.assertRaisesRegex(TwinError, "invalid bounds"):
                load_fills(str(path))

    def test_rejects_duplicate_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = (DATA/"demo_fills.csv").read_text().splitlines(); lines[2] = lines[2].replace("00:01:00", "00:00:00")
            path = Path(tmp)/"bad.csv"; path.write_text("\n".join(lines))
            with self.assertRaisesRegex(TwinError, "strictly increase"):
                load_fills(str(path))
