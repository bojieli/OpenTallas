import gzip
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "die_plan"))
import head_serdes_ve_event as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "physical/die_plan/s81_head/plan_of_record/l48ve"
BASE = ROOT / "physical/die_plan/s81_head/plan_of_record/l48vd"


def test_remap_exports_same_depth_nearest_site():
    T = {"reset_start_raw_exports": [{"port": "p0", "instance": "u_rrl_3", "net": "rst_rl_3", "xy_um": [10.0, 10.0]}]}
    rows = E.remap_exports(T, [("rst_rl_3", 2, 10.0, 10.0, 1)], [("rst_rl_5", 2, 30.0, 10.0, 0), ("rst_rl_6", 1, 10.0, 10.0, 0)])
    assert rows[0]["new"] == ["u_rrl_5", "rst_rl_5"] and rows[0]["relay_moved_um"] == 20.0
    assert T["reset_start_raw_exports"][0]["xy_um"] == [10.0, 10.0]


@pytest.mark.skipif(not (DIR.is_dir() and BASE.is_dir()), reason="sparse tree without the plan dirs")
def test_stored_event():
    plan = json.loads(gzip.open(DIR / "source_plan.json.gz", "rt").read())
    base = json.loads(gzip.open(BASE / "source_plan.json.gz", "rt").read())
    rec = json.loads((DIR / "l48ve_event.json").read_text())
    T, B = plan["partition_types"]["hd_serdes"], base["partition_types"]["hd_serdes"]
    ck = T["clock"]
    # the SC clock taps: clk keeps the die-spine anchor, clk_t1 (E) and clk_t2 (W reset/START OUT pins) added
    assert ck["tap_mode"] == "explicit" and ck["control_sinks"] is True
    assert [t["name"] for t in ck["taps"]] == ["clk", "clk_t1", "clk_t2"]
    assert ck["taps"][0]["xy"] == B["clock"]["tap_um"]
    assert "core_taps" not in ck and rec["core_tap_deferred"]["port"] == "clk_c0"
    assert all(0 < t["load"] <= ck["tap_max_sinks"] and t["reach_um"] <= ck["tap_radius_um"] for t in rec["taps"])
    # pma_rck stays one tree: the pad clock and edge clocks are untouched
    assert ck["pad_clock"] == B["clock"]["pad_clock"] and ck["edge_clocks"] == B["clock"]["edge_clocks"]
    # only hd_serdes moved (sink bins repointed to this record's copies); lanes and straps unchanged
    def others(p):
        return json.loads(json.dumps({k: v for k, v in p["partition_types"].items() if k != "hd_serdes"})
                          .replace("/l48ve/assets/", "/l48vd/assets/"))
    assert others(plan) == others(base)
    assert {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()} == \
        {k: v["cycles"] for k, v in base["latency"]["lanes"].items()}
    assert {k: v for k, v in T.items() if k not in ("clock", "reset_start_raw_exports")} == \
        {k: v for k, v in B.items() if k not in ("clock", "reset_start_raw_exports")}
    assert [e["xy_um"] for e in T["reset_start_raw_exports"]] == [e["xy_um"] for e in B["reset_start_raw_exports"]]
    w = gzip.open(DIR / "published/ot_s81hd_serdes.sv.gz", "rt").read()
    assert "input  wire clk_t1," in w and "input  wire clk_t2," in w and "clk_c0" not in w
