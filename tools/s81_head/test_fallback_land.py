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
    assert all(len(S.tap_grid(P, tn)) == 1 for tn in P.types)                        # one entry per partition
    # DIE-HEAD-5: hd_tile keeps its 5 EARLY core taps (one per hard core clock pin ft_mstrap_i) at the signed
    # capsules' measured mean insertion (12.3 v5.0); every other type has none.  Grid/sink taps still collapse.
    import head_plan_coretaps_signed as HS
    cap = ROOT / "results" / "head_core_clockfreeze_release"
    signed = {mod: HS.means(cap, name) for mod, name in HS.MOD.items()}
    mods = {c["inst"]: c["module"] for c in P.types["hd_tile"]["hard_cores"]}
    assert {tn for tn in P.types if S.core_taps(P, tn)} == {"hd_tile"}
    ct = S.core_taps(P, "hd_tile")
    assert len(ct) == 5 and sorted(tp["name"].rsplit(".", 1)[0] for *_, tp in ct) == sorted(mods)
    for port, x, y, tp in ct:
        assert tp["kind"] == "core" and tp["name"].endswith(".ft_mstrap_i")
        assert (tp["insertion_ps"], tp["insertion_ff_ps"]) == signed[mods[tp["name"].rsplit(".", 1)[0]]]
    assert [tp for tp in P.types["hd_tile"]["clock"]["taps"] if tp.get("kind") != "core"] == []
    taps = DT.clock_taps(P)
    assert DT.build_htree(P, taps, 300.0) == DT.build_htree(P, taps, 300.0, False)   # default unchanged
    nd = DT.build_htree(P, taps, 300.0, True)
    leaf_levels = {n["level"] for n in nd.values() if n["taps"]}
    assert len(leaf_levels) == 1                                                       # equal-depth leaves


def test_tree_site_legal(tmp_path):
    import types
    import die_trial as DT
    import schema as S
    out = tmp_path / "fb1.json"
    F.cmd_variant(types.SimpleNamespace(plan=str(PLAN), out=str(out)))
    P = S.Plan(S.load(str(out)))
    *_, m = DT.clock_kit(P, tmp_path / "clk", 300.0, 450.0, True, True)
    assert m["site_legal"]["illegal"] == {} and m["site_legal"]["forbidden_rects"] == 1332


def test_tree_site_slide_keeps_lengths(tmp_path):
    import types
    import die_trial as DT
    import schema as S
    out = tmp_path / "fb1.json"
    F.cmd_variant(types.SimpleNamespace(plan=str(PLAN), out=str(out)))
    P = S.Plan(S.load(str(out)))
    *_, m = DT.clock_kit(P, tmp_path / "clk", 300.0, 450.0, True, False, True)
    assert m["site_legal"]["mode"] == "slide" and m["site_legal"]["illegal"] == {}


def test_dataflow_monitor_uniform_tree_bus():
    import clock_landing_plan as CLP
    import schema as S
    p = _plan()
    t = F.table(p, "part")
    tb, parent, dist = CLP._dataflow_tree(S.Plan(p), t, {x["id"]: x for x in p["ports"]}, "ctl")
    assert tb["hd_tile"] == "o" and tb["hd_ctl"] is None and parent["ctl"] is None
    assert all(dist[c] < dist[n] for n, c in parent.items() if c is not None)


def test_region_map_granularity(tmp_path):
    """DIE-HEAD 10-27: opt-in map:FILE granularity; only ports between different map regions land (feed40 map)."""
    p = _plan()
    m = ROOT / "results" / "die_head_1027" / "maps" / "feed36b.json"
    if not m.is_file():
        return
    pr = json.loads(m.read_text())["part_region"]
    t = F.table(p, "map:" + str(m))
    assert len(t["regions"]) == len(set(pr.values())) == 40
    assert len(t["ports"]) == 94 and all(pr[r["src"]] != pr[r["dst"]] for r in t["ports"])
    assert F.head_pass(p, t)["head_pass_crossings"] == 4


def test_region_monitor_walks_same_region_links():
    """DIE-HEAD-2 10-27: opt-in monitor="region": the observer walk follows same-region links as well as the landed
    crossings; dataflow (landed ports only) still fails closed on a multi-partition region map; default unchanged."""
    import pytest
    import clock_landing_plan as CLP
    import landing_contract as LC
    import schema as S
    p = _plan()
    m = ROOT / "results" / "die_head_1027" / "maps" / "feed36b.json"
    if not m.is_file():
        return
    t = F.table(p, "map:" + str(m))
    with pytest.raises(ValueError, match="cannot reach observer"):
        CLP.compose(p, t, str(PLAN), observer_part="ctl", monitor="dataflow")
    raw, side = CLP.compose(p, t, str(PLAN), observer_part="ctl", monitor="region")
    c = side["collector"]
    assert c["monitor"] == "region" and len(raw["partition_types"]) == 21
    assert {pn: x["type"] for pn, x in c["parts"].items()} == {q["name"]: q["type"] for q in raw["partitions"]}
    assert set(c["parts"]) == {q["name"] for q in p["partitions"]}
    for pn, x in c["parts"].items():                       # every part reaches ctl, potential strictly falls
        if x["parent"] is not None:
            assert c["parts"][x["parent"]]["potential"] < x["potential"]
    seams = [e for e in c["edges"] if e["seam"]]
    assert len(seams) == 94 and all(e["boot_transport_extra_cycles"] == 3 for e in seams)
    intra = [e for e in c["edges"] if not e["seam"]]
    assert intra and all(e["boot_transport_extra_cycles"] == 1 for e in intra)
    pr = json.loads(m.read_text())["part_region"]
    assert all(pr[e["src"]] == pr[e["dst"]] for e in intra)
    assert all(not t_["bands"] or t_["mask"]["inputs"] for t_ in c["types"].values())   # rings only on landed inputs
    assert c["placement_failures"] == [] and not LC.check(S.Plan(raw, str(PLAN)))["errors"]
