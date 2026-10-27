"""FALLBACK-HEAD tool checks on the canonical s81_head plan (plan-level, fast)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# ROOT-MERGE-22: tools/die_plan/fallback_land.py (FALLBACK-KV) shares the module name; s81_head must win.
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import fallback_land as F  # noqa: E402

PLAN = ROOT / "physical" / "die_plan" / "s81_head" / "die_plan.json"


def _plan():
    return json.loads(PLAN.read_text())


def test_part_regions_land_every_port():
    p = _plan()
    t = F.table(p, "part")
    assert len(t["regions"]) == len(p["partitions"])
    assert len(t["ports"]) == len(p["ports"])
    assert all(r["src_region"] != r["dst_region"] and r["added_cycles"] == 3 for r in t["ports"])


def test_uniform_masks_no_type_split():
    import clock_landings as CL
    p = _plan()
    req = CL.requirements(p, F.table(p, "part"))
    assert req["type_count_after"] == req["type_count_before"]


def test_head_pass_count():
    p = _plan()
    h = F.head_pass(p, F.table(p, "part"))
    assert h["head_pass_crossings"] == 37 and h["path"]["chain"] == 25


def test_variant_one_entry_and_htree_full_depth(tmp_path):
    import types
    import die_trial as DT
    import schema as S
    out = tmp_path / "fb1.json"
    F.cmd_variant(types.SimpleNamespace(plan=str(PLAN), out=str(out)))
    P = S.Plan(S.load(str(out)))
    assert all(len(S.tap_grid(P, tn)) == 1 and not S.core_taps(P, tn) for tn in P.types)
    taps = DT.clock_taps(P)
    assert DT.build_htree(P, taps, 300.0) == DT.build_htree(P, taps, 300.0, False)   # default unchanged
    nd = DT.build_htree(P, taps, 300.0, True)
    leaf_levels = {n["level"] for n in nd.values() if n["taps"]}
    assert len(leaf_levels) == 1                                                       # equal-depth leaves
