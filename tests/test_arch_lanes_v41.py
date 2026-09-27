"""The package lane split (tools/arch_lanes_v41.py): per-peer link bytes cost the rack's split real time, the adopted
split is never slower than the rack's at batch 1, and SerDes static power is on both machines."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/arch/v41_lanes.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_every_split_uses_the_package_lanes(rec):
    for r in rec["grid"]:
        assert r["tp"] + 2 * r["stage"] + r["switch"] + r["spare"] == rec["lanes_per_package"]


def test_rack_split_is_slower_than_the_overlap_assumption(rec):
    ref, rack = rec["ladder_top_overlap_assumed"]["1048576"], rec["rack_split_result"]["1048576"]
    assert rack["ar"] < ref["ar"] and rack["mtp"] < ref["mtp"]


def test_adopted_split_not_slower_than_rack(rec):
    assert rec["best_adopted"]
    for c in ("1048576", "200000"):
        for k in ("ar", "mtp"):
            assert rec["best_split"][c][k] >= rec["rack_split_result"][c][k] * (1 - 1e-4)


def test_serdes_static_on_both_machines(rec):
    s = rec["static_w"]
    assert s["rom_serdes"] > 3000 and s["rom_switch_w"] > 0   # the HBM side is in v41_hbm_switched.json
    for c, rows in rec["energy"].items():
        for k, v in rows.items():
            assert v["ratio_energy_with_static"] > 1.5, (c, k)
