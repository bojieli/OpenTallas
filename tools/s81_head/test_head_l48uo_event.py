import gzip
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "die_plan"))
import head_l48uo_event as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "physical/die_plan/s81_head/plan_of_record/l48uo"


def _plan():
    return {"clock": {"landing_network": {"count_aligned_cycles": {"a": 3, "b": 1, "c": 3}}},
            "lanes": [{"id": "L", "ports": ["a", "b"]}, {"id": "M", "ports": ["c"]}],
            "partition_types": {"x": {"clock": {"sink_bins_file": "old/assets/sink_bins_0.json"}}, "y": {"clock": {}}}}


def test_carry_sched_lat_only_declared_rises():
    p = _plan()
    rows = E.carry_sched_lat(p, {"count_aligned": {"ports": {"a": {"sched_lat": 4}, "b": {"sched_lat": 1}, "c": {"sched_lat": 3}}}})
    assert rows == [dict(port="a", lane="L", old=3, new=4)]
    assert p["clock"]["landing_network"]["count_aligned_cycles"]["a"] == 4
    with pytest.raises(ValueError):
        E.carry_sched_lat(_plan(), {"count_aligned": {"ports": {"a": {"sched_lat": 2}, "b": {"sched_lat": 1}, "c": {"sched_lat": 3}}}})
    with pytest.raises(ValueError):
        E.carry_sched_lat(_plan(), {"count_aligned": {"ports": {"a": {"sched_lat": 3}}}})


def test_repoint_sink_bins():
    p = _plan()
    assert E.repoint_sink_bins(p, "new") == {"x": "new/assets/sink_bins_0.json"}
    assert p["partition_types"]["x"]["clock"]["sink_bins_file"] == "new/assets/sink_bins_0.json"


@pytest.mark.skipif(not DIR.is_dir(), reason="sparse tree without the plan dir")
def test_stored_event():
    """clean checkout: every sink_bins_file is a plain tracked file; the schedule is the hardware's; sidecar = 90d006"""
    from regen_schedule_constants import generate
    plan = json.loads(gzip.open(DIR / "source_plan.json.gz", "rt").read())
    bins = {t["clock"]["sink_bins_file"] for t in plan["partition_types"].values() if t.get("clock", {}).get("sink_bins_file")}
    assert len(bins) == 9 and all((ROOT / b).is_file() and "/l48uo/assets/" in b for b in bins)
    for t in plan["partition_types"].values():
        for h in t.get("hard_cores", []):
            assert not h.get("pins_file") or h["pins_file"].startswith("/") or (DIR / h["pins_file"]).is_file(), h["pins_file"]
    nd = plan["partition_types"]["hd_serdes"]["clock"]["native_domains"]
    assert (DIR / nd["census_file"]).is_file() and all((DIR / c["census_file"]).is_file() for c in nd["children"])
    side = json.loads(gzip.open(DIR / "source_sidecar.json.gz", "rt").read())
    assert plan["clock"]["landing_network"]["count_aligned_cycles"] == {k: v["sched_lat"] for k, v in side["count_aligned"]["ports"].items()}
    t = generate(plan)["transport"]
    assert (t["total_cycles"], t["spine"]["cycles"], t["gather_worst"]) == (336, 174, dict(lane="m0S_rx", cycles=81))
