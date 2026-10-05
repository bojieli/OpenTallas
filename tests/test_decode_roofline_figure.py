"""The decode-roofline record (tools/decode_roofline_figure.py) reproduces from this tree's records, and its V4.1 ROM
point is the adopted design point's headline (collective exposure measured in RTL)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decode_roofline_figure as F  # noqa: E402


def test_record_is_current():
    assert F.main(["--check"]) == 0


def test_v41_rom_point_is_the_design_point_headline():
    rec = json.loads(F.OUT_JSON.read_text())
    dp = json.loads((ROOT / "results/arch/v41_lanes.json").read_text())["design_point"]
    s3 = next(r for r in rec["models"]["v41"]["ladders"]["per_user"] if r["step"] == "S3")
    assert abs(s3["value"] - dp["1048576"]["ar"]) / dp["1048576"]["ar"] < 1e-5
    assert "C7 bench tails" in s3["evidence"]
