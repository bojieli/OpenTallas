import gzip
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "die_plan"))
import head_ctl_n_vd_event as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "physical/die_plan/s81_head/plan_of_record/l48vd"
BASE = ROOT / "physical/die_plan/s81_head/plan_of_record/l48uo"


def test_remap_exports_same_depth_nearest_site():
    T = {"reset_start_raw_exports": [
        {"port": "p0", "instance": "u_rrl_3", "net": "rst_rl_3", "xy_um": [10.0, 10.0]},
        {"port": "p1", "instance": "u_rrl_7", "net": "rst_rl_7", "xy_um": [50.0, 10.0]}]}
    por = [("rst_rl_3", 1, 10.0, 10.0, 1), ("rst_rl_7", 2, 50.0, 10.0, 1)]
    new = [("rst_rl_0", 1, 10.0, 10.0, 0), ("rst_rl_4", 2, 70.0, 10.0, 0), ("rst_rl_5", 1, 50.0, 10.0, 0)]
    rows = E.remap_exports(T, por, new)
    assert [r["new"] for r in rows] == [["u_rrl_0", "rst_rl_0"], ["u_rrl_4", "rst_rl_4"]]
    assert [r["relay_moved_um"] for r in rows] == [0.0, 20.0]
    assert T["reset_start_raw_exports"][1]["xy_um"] == [50.0, 10.0]     # the export pin keeps its site
    with pytest.raises(ValueError):
        E.remap_exports({"reset_start_raw_exports": [dict(T["reset_start_raw_exports"][0], net="rst_rl_0")]},
                        [("rst_rl_0", 3, 0.0, 0.0, 0)], new)


@pytest.mark.skipif(not (DIR.is_dir() and BASE.is_dir()), reason="sparse tree without the plan dirs")
def test_stored_event():
    from regen_schedule_constants import generate
    plan = json.loads(gzip.open(DIR / "source_plan.json.gz", "rt").read())
    base = json.loads(gzip.open(BASE / "source_plan.json.gz", "rt").read())
    rec = json.loads((DIR / "l48vd_event.json").read_text())
    T, B = plan["partition_types"]["hd_ctl_n"], base["partition_types"]["hd_ctl_n"]
    # die clock (B): the l48uo taps keep names and sites, four are appended
    taps = [t for t in T["clock"]["taps"] if t.get("kind") != "core"]
    assert T["clock"]["tap_mode"] == "explicit" and [t["name"] for t in taps] == ["clk"] + [f"clk_t{i}" for i in range(1, 14)]
    assert rec["taps_kept"] == ["clk"] + [f"clk_t{i}" for i in range(1, 10)]
    assert max(t["reach_um"] for t in rec["taps"]) <= T["clock"].get("tap_radius_um", 200)
    # only hd_ctl_n and the landing network moved
    def others(p):
        return json.loads(json.dumps({k: v for k, v in p["partition_types"].items() if k != "hd_ctl_n"})
                          .replace("/l48vd/assets/", "/l48uo/assets/"))
    assert others(plan) == others(base)
    assert plan["clock"]["landing_network"]["input_pin_cycles"] == {"coll_WN3_u__0": 1, "coll_WN3_d__0": 1}
    assert T["clock"]["landing_ring_wreg"]["read_chunk"] == 32 and T["clock"]["landing_ring_wreg"]["write_tail"] is True
    assert {s["name"]: s["stations"] for s in T["ft_slots"]}["unit_ft"] == 2
    lanes = {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}
    blanes = {k: v["cycles"] for k, v in base["latency"]["lanes"].items()}
    assert {k: (blanes[k], lanes[k]) for k in lanes if lanes[k] != blanes[k]} == \
        {"coll_WN3_u": (11, 12), "coll_WN3_d": (11, 12), "unit_lep": (5, 6)}
    assert [s[1:] for s in rec["die_top_straps"]] == [["strap_ca_k_w3d_i", 5, 7], ["strap_ca_k_w3u_i", 8, 10]]
    bins = {t["clock"]["sink_bins_file"] for t in plan["partition_types"].values() if t.get("clock", {}).get("sink_bins_file")}
    assert bins and all((ROOT / b).is_file() and "/l48vd/assets/" in b for b in bins)
    # the transport schedule is the l48uo one: the moved lanes are off the worst gather
    t = generate(plan)["transport"]
    assert (t["total_cycles"], t["spine"]["cycles"], t["gather_worst"]) == (336, 174, dict(lane="m0S_rx", cycles=81))
