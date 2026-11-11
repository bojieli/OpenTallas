"""Tests for tools/die_plan/route_supply.py (PLAN-ROUTE-1, advisory plan-time routing supply vs demand)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_supply as rs  # noqa: E402


def lef(path, name, w, h, layers):
    obs = "".join(f"    LAYER {L} ;\n      RECT 0 0 {w} {h} ;\n" for L in layers)
    path.write_text(f"MACRO {name}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {w} BY {h} ;\n"
                    f"  OBS\n{obs}  END\nEND {name}\nEND LIBRARY\n")


def pins(path, side_x, n, h, bus="d"):
    path.write_text(json.dumps({"pins": [{"name": f"{bus}[{i}]", "layer": "M5", "x": side_x,
                                          "y": 5 + i * (h - 10) / max(n - 1, 1)} for i in range(n)]}))


def plan(tmp, layers_a=("M1", "M2", "M3", "M4", "M5"), n=4000, macro=True):
    """two small cores left/right of a tall blocking macro; core_conns joins them across it."""
    lef(tmp / "blk.lef", "blk", 200, 400, layers_a)
    lef(tmp / "c.lef", "c", 40, 400, ("M1", "M2", "M3", "M4", "M5"))
    pins(tmp / "a.json", 40, n, 400, "d")
    pins(tmp / "b.json", 0, n, 400, "d")
    hc = [dict(inst="u_a", module="c", origin_um=[10, 50], outline_um=[40, 400], orient="R0", lef="c.lef",
               pins_file="a.json"),
          dict(inst="u_b", module="c", origin_um=[350, 50], outline_um=[40, 400], orient="R0", lef="c.lef",
               pins_file="b.json")]
    if macro:
        hc.append(dict(inst="u_m", module="blk", origin_um=[100, 0], outline_um=[200, 500], orient="R0",
                       lef="blk.lef", pins_file="none.json"))
    P = {"schema": "opentallas.die_plan.v1", "die": {"name": "tst"},
         "partition_types": {"t": {"outline_um": [400, 500], "hard_cores": hc}}}
    (tmp / "plan.json").write_text(json.dumps(P))
    (tmp / "core_conns.json").write_text(json.dumps({"t": {"u_a": {"d": ["core:u_b"]}, "u_b": {"d": ["core:u_a"]}}}))
    return tmp / "plan.json"


def run(tmp, *extra):
    out = tmp / "out"
    rc = rs.main([str(tmp / "plan.json"), "--die", "tst", "--repo", str(tmp), "--out", str(out),
                  "--core-conns", str(tmp / "core_conns.json"), "--release-cache", str(tmp / "nope.json"),
                  "--views", str(tmp / "noviews.json")] + list(extra))
    d = json.loads((out / "route_supply_tst.json").read_text())
    return rc, d["rows"][0], (out / "route_supply_tst.tsv").read_text()


def test_macro_crossing_flags_h_over_core(tmp_path):
    plan(tmp_path, n=8000)
    rc, r, tsv = run(tmp_path)
    assert rc == 0                                    # advisory: never a failing exit
    assert r["verdict"] == "FLAG"
    assert r["worst"]["dir"] == "H" and r["worst"]["region"] in ("core", "street")
    assert r["regions"]["core_H"]["p99"] > 1.0
    assert r["worst"]["layer"] == "M6" or r["worst"]["region"] != "core"
    assert tsv.splitlines()[0].startswith("die\ttype\tverdict")


def test_no_macro_same_nets_ok(tmp_path):
    plan(tmp_path, macro=False, n=1500)
    _, r, _ = run(tmp_path)
    assert r["regions"].get("open_H", {}).get("p99", 0) < 1.0


def test_memory_macro_is_classified_from_lef_not_name(tmp_path):
    plan(tmp_path, layers_a=("M1", "M2", "M3", "M4"), n=1500)
    _, r, _ = run(tmp_path)
    assert r["mem_macros"] == 1                         # OBS top M4 -> SRAM/ROM class, name "blk" says nothing
    assert "mem_H" in r["regions"]


def test_template_lef_is_capped_and_views_table_wins(tmp_path):
    plan(tmp_path, layers_a=("M1", "M2", "M3", "M4", "M5", "M6", "M7"), n=1500)
    _, r, _ = run(tmp_path)
    assert any(k.startswith("plan-template") for k in r["obs_src"])
    assert "blk" in r["provisional_children"]
    (tmp_path / "views.json").write_text(json.dumps({"views": {"blk": {"obs_top": "M7", "src": "signed"}}}))
    out = tmp_path / "out2"
    rs.main([str(tmp_path / "plan.json"), "--die", "tst", "--repo", str(tmp_path), "--out", str(out),
             "--core-conns", str(tmp_path / "core_conns.json"), "--release-cache", str(tmp_path / "nope.json"),
             "--views", str(tmp_path / "views.json")])
    r2 = json.loads((out / "route_supply_tst.json").read_text())["rows"][0]
    assert "blk" not in r2["provisional_children"]
    # a signed view blocking M6/M7 removes the only H/V layers over the macro -> worse than the capped template
    assert r2["regions"]["core_H"]["p99"] > r["regions"]["core_H"]["p99"]


def test_porous_need_free_reported(tmp_path):
    plan(tmp_path, n=2500)
    _, r, _ = run(tmp_path)
    p = r["porous"]["H"]
    assert p["layer"] == "M4"
    assert p["need_free"] is None or 0.0 <= p["need_free"] <= 1.0
    assert p["p99_all_free"] <= p["p99_now"]


def test_pin_table_shapes():
    assert list(rs._pin_iter({"pins": [{"name": "a[0]", "x": 1, "y": 2}]})) == [("a[0]", [1, 2])]
    assert list(rs._pin_iter([{"name": "b", "xy_um": [3, 4]}])) == [("b", [3, 4])]
    assert list(rs._pin_iter({"pins": {"c": [5, 6]}})) == [("c", [5, 6])]


def test_density_from_measured_cells_and_cohort_base(tmp_path):
    plan(tmp_path, macro=False, n=200)
    P = json.loads((tmp_path / "plan.json").read_text())
    P["partition_types"]["t__cl0123abcd"] = P["partition_types"]["t"]
    (tmp_path / "plan.json").write_text(json.dumps(P))
    (tmp_path / "cells.json").write_text(json.dumps({"tst": {"t": {"cells": 100000, "src": "synth"}}}))
    out = tmp_path / "outd"
    rs.main([str(tmp_path / "plan.json"), "--die", "tst", "--repo", str(tmp_path), "--out", str(out),
             "--core-conns", str(tmp_path / "core_conns.json"), "--release-cache", str(tmp_path / "nope.json"),
             "--views", str(tmp_path / "noviews.json"), "--cells", str(tmp_path / "cells.json")])
    rows = {r["type"]: r for r in json.loads((out / "route_supply_tst.json").read_text())["rows"]}
    for n in ("t", "t__cl0123abcd"):
        # soft area = outline minus the two cores; measured synth counts the type top only
        assert rows[n]["soft_um2"] < 400 * 500
        assert rows[n]["regions"]["dens_A"]["p99"] == round(100000 / rows[n]["soft_um2"], 4)   # > 0.5 >= 0.42
        assert rows[n]["verdict"] == "FLAG" and rows[n]["flag_regions"][0][0] == "dens_A"
    assert "base of" in rows["t__cl0123abcd"]["cells_basis"]


def test_flags_append_and_watch_skip_unchanged(tmp_path):
    import route_supply_flags as F
    import route_supply_watch as W
    plan(tmp_path, n=8000)
    rc, _, _ = run(tmp_path)
    tsv = tmp_path / "FLAGS.tsv"
    F.main([str(tmp_path / "out"), "--tsv", str(tsv), "--stamp", "s1", "--plans", f"tst={tmp_path / 'plan.json'}"])
    lines = tsv.read_text().splitlines()
    assert lines[0].split("\t")[:3] == ["stamp", "main", "die"] and len(lines) == 2
    row = dict(zip(lines[0].split("\t"), lines[1].split("\t")))
    assert row["flagged"] == "yes" and row["plan_sha"] == F.sha(tmp_path / "plan.json")
    pl = tmp_path / "plans.jsonl"
    pl.write_text(json.dumps({"die": "tst", "plan": "plan.json", "refs": []}) + "\n")
    W.main(["--repo", str(tmp_path), "--tsv", str(tsv), "--out-root", str(tmp_path / "w"), "--plans", str(pl)])
    assert len(tsv.read_text().splitlines()) == 2          # same plan sha: nothing re-run, nothing appended


def test_grt_transition_halving_m6_over_m5_obs(tmp_path):
    """OpenROAD halves M6 over a macro M5 OBS (adjustTransitionLayers): core_H doubles vs --no grt rules."""
    plan(tmp_path, n=2500)
    _, r1, _ = run(tmp_path)
    rs_cfg = rs.DEFAULTS.copy()
    obs = {L: rs.np.zeros((1, 1)) for L in rs.LAYERS}
    obs["M5"][:] = 1.0
    obs["M6"][:] = 0.0
    rs.grt_macro_rules(obs)
    assert obs["M7"][0, 0] == 0.0                      # M7 inherits M6 OBS only
    obs["M6"][:] = 1.0
    rs.grt_macro_rules(obs)
    assert obs["M7"][0, 0] == 1.0
    assert "M6" in rs.GRT_TRANSITION and "M2" not in rs.GRT_TRANSITION
    assert r1["regions"]["core_H"]["p99"] > 1.0 and rs_cfg["bin_um"] > 0


def test_kit_lef_replaces_whole_block_template(tmp_path):
    """a plan M1-M7 template defers to the kit's real view LEF (route_supply_kit_views.json) when one exists."""
    plan(tmp_path, layers_a=("M1", "M2", "M3", "M4", "M5", "M6", "M7"), n=1500)
    _, r0, _ = run(tmp_path)
    kv = tmp_path / "kv.json"
    kv.write_text(json.dumps({"tst": {"blk": {"obs": {"M1": .9, "M2": .9, "M3": .5, "M4": .4, "M5": .25,
                                                      "M6": .1, "M7": .1}}}}))
    _, r1, _ = run(tmp_path, "--kit-views", str(kv))
    assert any(k.startswith("plan-template") for k in r0["obs_src"])
    assert "kit-lef" in r1["obs_src"] and not any(k.startswith("plan-template") for k in r1["obs_src"])
    assert r1["regions"]["core_H"]["p99"] < r0["regions"]["core_H"]["p99"]   # porous real view frees M4/M6


def test_margin_default_and_what_if_options_run(tmp_path):
    plan(tmp_path, n=2500)
    assert rs.DEFAULTS["margin_bins"] == 9
    _, r9, _ = run(tmp_path)
    _, r2, _ = run(tmp_path, "--margin-bins", "2")
    _, rw, _ = run(tmp_path, "--pin-escape", "--station-spread")
    assert r9["regions"]["core_H"]["p99"] <= r2["regions"]["core_H"]["p99"] + 1e-9   # wider detour pool never worse
    assert rw["verdict"] in ("FLAG", "ok")


def test_grt_edge_halving_mode_between_full_and_none(tmp_path):
    """GRT-PATCH-1 edge image: halving only within K gcells of macro edges/pins -> core_H between stock and none."""
    plan(tmp_path, n=2500)
    _, rf, _ = run(tmp_path)
    _, re_, _ = run(tmp_path, "--grt-halving", "edge", "--grt-edge-gcells", "2")
    _, rb, _ = run(tmp_path, "--grt-halving", "edge", "--grt-edge-gcells", "400")
    _, rn, _ = run(tmp_path, "--grt-halving", "none")
    f, e, b, n = (r["regions"]["core_H"]["p99"] for r in (rf, re_, rb, rn))
    assert n <= e <= f and n < f
    assert abs(b - f) < 1e-6                           # K beyond the macro half-width = the stock image
    g = rs.Grid(400, 500, 10.8)
    w = rs.grt_halving_weight(g, [(100, 0, 300, 500, {"inst": "m"})], {"m": [("d", 200, 250)]}, 2)
    assert 0.1 < w[0, 9] < 0.3                         # edge bin: only the 1.17 um band along x=100 and y=0
    assert w[10, 15] == 0.0 and w[23, 18] > 0.0         # interior: halved only around the pin at (200, 250)
    assert w.max() <= 1.0


def test_grt_edge_modes_follow_grt_patch_1(tmp_path):
    """edge (OBS tile union boundary + all pins incl. PG on L-1/L/L+1) vs edge_outline (instance bbox + signal pins):
    a porous M5 view with PG straps stays halved under edge and is freed inside under edge_outline."""
    plan(tmp_path, n=2500)
    strips = "".join(f"      RECT {x} 0 {x + 2} 400 ;\n" for x in range(0, 200, 4))
    straps = "".join(f"        RECT {x} 0 {x + 0.3} 400 ;\n" for x in range(3, 200, 3))
    lefp = tmp_path / "blk.lef"
    lefp.write_text(
        "MACRO blk\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE 200 BY 400 ;\n"
        "  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M7 ;\n" + straps + "    END\n  END VDD\n  OBS\n"
        + "".join(f"    LAYER {L} ;\n      RECT 0 0 200 400 ;\n" for L in ("M1", "M2", "M3", "M4"))
        + "    LAYER M5 ;\n" + strips + "  END\nEND blk\nEND LIBRARY\n")
    rs._LEF_CACHE.clear()
    rs._EDGE_CACHE.clear()
    _, pf, _ = run(tmp_path)
    _, pe, _ = run(tmp_path, "--grt-halving", "edge")
    _, po, _ = run(tmp_path, "--grt-halving", "edge_outline")
    # region p99 also sees the cores beside the macro; the per-tile shares are checked below
    assert max(po["regions"]["core_H"]["p99"], pe["regions"]["core_H"]["p99"]) <= pf["regions"]["core_H"]["p99"]
    sh = rs.lef_edge_share(lefp, 2, rs.GRT_GCELL_UM)
    assert sh["M5"] > 0.95                     # 2-um strips: every OBS tile within 2 gcells of a free tile
    assert sh["M3"] < 0.05                     # solid M3, no pins on M3/M4/M5: only the rim
    assert sh["M4"] < 0.05 and sh["M5"] > sh["M4"]
    sh6 = rs.edge_share(rs.lef_shapes(lefp.read_text()), (2,), rs.GRT_GCELL_UM)["2"]
    assert sh6 == sh
    g = rs.Grid(400, 500, 10.8)
    mr = [(100, 0, 300, 400, {"inst": "m"})]
    rs._VIEW_SRC.clear()
    rs._VIEW_SRC["m"] = ("lef", lefp)
    w = rs.grt_halving_weight_obs(g, rs.coverage(g, mr), mr, {}, 2, {}, [])
    wo = rs.grt_halving_weight(g, mr, {}, 2)
    assert w["M5"][18, 18] > 0.95 and wo[18, 18] == 0.0
    # PG straps on M7 (L+1 of M6) only count for B = M5
    solid = tmp_path / "s.lef"
    solid.write_text(lefp.read_text().replace(strips, "      RECT 0 0 200 400 ;\n"))
    assert rs.lef_edge_share(solid, 2, rs.GRT_GCELL_UM)["M5"] > 0.9   # straps every 3 um, halo 2 gcells


def test_core_conns_from_plan_dir_and_refs_merged_per_type(tmp_path):
    """a materialised plan dir (HBM) carries core_conns.json beside die_plan.json: route_supply reads it (and .gz in a
    ref dir) instead of falling back to the all-core centroid; the plan dir wins per type over the die dir."""
    import gzip
    plan(tmp_path, n=1500)
    pd = tmp_path / "por"
    pd.mkdir()
    (pd / "plan.json").write_text((tmp_path / "plan.json").read_text())
    out = tmp_path / "o"
    rs.main([str(pd / "plan.json"), "--die", "tst", "--repo", str(tmp_path), "--out", str(out),
             "--release-cache", str(tmp_path / "nope.json"), "--views", str(tmp_path / "noviews.json")])
    r0 = json.loads((out / "route_supply_tst.json").read_text())["rows"][0]
    assert r0["model"] == "fallback"
    (pd / "core_conns.json").write_text((tmp_path / "core_conns.json").read_text())
    rs.main([str(pd / "plan.json"), "--die", "tst", "--repo", str(tmp_path), "--out", str(out),
             "--release-cache", str(tmp_path / "nope.json"), "--views", str(tmp_path / "noviews.json")])
    r1 = json.loads((out / "route_supply_tst.json").read_text())["rows"][0]
    assert r1["model"] == "core_conns" and r1["conns_src"].endswith("por/core_conns.json")
    ref = tmp_path / "physical" / "die_plan" / "old"
    ref.mkdir(parents=True)
    with gzip.open(ref / "core_conns.json.gz", "wt") as f:
        json.dump({"t": {}, "t2": {"u_a": {"d": ["core:u_b"]}}}, f)
    src = rs.conns_sources(tmp_path / "nodie", pd, [str(ref)])
    assert [p.name for p in src] == ["core_conns.json", "core_conns.json.gz"]
    m = rs.load_conns(tmp_path / "nodie", None, pd, [str(ref)])
    assert set(m) == {"t", "t2"} and m["t"]["u_a"]["d"] == ["core:u_b"]        # plan dir wins for t


def test_stale_bus_name_goes_to_nearest_same_direction_face_bus(tmp_path):
    plan(tmp_path, n=400)
    P = json.loads((tmp_path / "plan.json").read_text())
    P["partition_types"]["t"]["buses"] = [{"name": "N_i", "dir": "in", "face": "W", "width": 400, "window_um": [50, 450]}]
    (tmp_path / "plan.json").write_text(json.dumps(P))
    (tmp_path / "core_conns.json").write_text(json.dumps({"t": {"u_a": {"d": ["bus:OLD7_i", "tap:u_a"]},
                                                                "u_b": {"d": ["core:u_a"]}}}))
    _, r, _ = run(tmp_path)
    assert any("nearest same-direction face bus" in n for n in r["notes"])
    assert not any("not placed" in n for n in r["notes"])          # tap: is the clock, not unresolved


def test_core_dest_with_port_suffix_resolves(tmp_path):
    """core_conns_from_bind writes core:<inst>.<port>; route_supply resolves it to the core like core:<inst>."""
    plan(tmp_path, n=800)
    _, r0, _ = run(tmp_path)
    (tmp_path / "core_conns.json").write_text(json.dumps({"t": {"u_a": {"d": ["core:u_b.d"]}, "u_b": {"d": ["core:u_a.d"]}}}))
    _, r1, _ = run(tmp_path)
    assert not any("not placed" in n for n in r1["notes"])
    assert abs(r1["regions"]["core_H"]["p99"] - r0["regions"]["core_H"]["p99"]) < 1e-6
    assert rs._names_core(["core:u_a.d"], "u_a") and not rs._names_core(["core:u_a.x.y"], "u_a")


def _t51_like(tmp, obs_max=True):
    """two abutting solid M1-M7 children (native split) tiling the outline; a 1104-bit E->W ft slot whose stations
    live inside both children (stations_in)."""
    L7 = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")
    lef(tmp / "w.lef", "cw", 300, 480, L7)
    lef(tmp / "e.lef", "ce", 380, 480, L7)
    hc = [dict(inst="u_w", module="cw", origin_um=[8, 10], outline_um=[300, 480], orient="R0", lef="w.lef",
               pins_file="none.json"),
          dict(inst="u_e", module="ce", origin_um=[316, 10], outline_um=[380, 480], orient="R0", lef="e.lef",
               pins_file="none.json")]
    if obs_max:
        for h in hc:
            h["obs_max"] = "M7"
    ft = dict(name="ft0", stations_in=["u_e", "u_w"], in_face="E", out_face="W", width=4416,
              in_window_um=[20, 240], out_window_um=[20, 240], regs_um=[[704, 130], [500, 130], [150, 130], [4, 130]])
    P = {"schema": "opentallas.die_plan.v1", "die": {"name": "tst"},
         "partition_types": {"t": {"outline_um": [704, 500], "hard_cores": hc, "ft_slots": [ft],
                                   "clock": {"landing_contract": {"bands": {"ft0_i": {
                                       "rect_um": [20, 100, 120, 140], "width": 4416,
                                       "padded_data_storage_flops": 20000}}}}}}}
    (tmp / "plan.json").write_text(json.dumps(P))
    (tmp / "core_conns.json").write_text(json.dumps({}))


def test_ft_inside_hard_cores_is_not_parent_wire_over_them(tmp_path):
    """CPL-S81-STN t51: ft slots whose stations_in are the hard cores are child-internal; parent wire is only the
    face -> core, core -> core (seam) and core -> face legs."""
    _t51_like(tmp_path)
    _, r0, _ = run(tmp_path, "--ft-internal-as-parent", "--template-cap-default")
    _, r1, _ = run(tmp_path)
    assert r0["verdict"] == "FLAG" and r0["regions"]["core_H"]["p99"] > 3
    assert r1["ft_core_internal_bits"] == 4416 and r0["ft_core_internal_bits"] == 0
    assert r1["ring_bands_core_internal"] == 1 and r0["ring_bands_core_internal"] == 0
    assert r1["verdict"] != "FLAG"
    assert r1["regions"].get("core_H", {}).get("p99", 0) < 0.4 * r0["regions"]["core_H"]["p99"]
    assert r1["wirelength_mm"] < 0.1 * r0["wirelength_mm"]


def test_template_cap_follows_plan_obs_max(tmp_path):
    """a whole-block template is capped at the plan's obs_max (M7), not the M5 default: no M6 credit over it."""
    _t51_like(tmp_path)
    _, r1, _ = run(tmp_path, "--ft-internal-as-parent")
    _, r0, _ = run(tmp_path, "--ft-internal-as-parent", "--template-cap-default")
    assert any("M7 obs_max" in k for k in r1["obs_src"]) and any("M5)" in k for k in r0["obs_src"])
    assert r1["regions"]["core_H"]["p99"] > r0["regions"]["core_H"]["p99"]
    _t51_like(tmp_path, obs_max=False)
    _, r2, _ = run(tmp_path, "--ft-internal-as-parent")
    assert any("capped M5)" in k for k in r2["obs_src"])


def test_empty_core_conns_entry_is_unchecked_not_glue(tmp_path):
    plan(tmp_path, n=800)
    (tmp_path / "core_conns.json").write_text(json.dumps({"t": {"u_a": {}, "u_b": {}}}))
    _, r0, _ = run(tmp_path, "--empty-conns-glue")
    _, r1, _ = run(tmp_path)
    assert r0["glue_pins"] == 1600 and r0["unchecked_pins"] == 0
    assert r1["glue_pins"] == 0 and r1["unchecked_pins"] == 1600 and r1["verdict"] == "UNCHECKED"
    assert any("UNCHECKED" in n for n in r1["notes"])
    import route_supply_flags as rf
    out = tmp_path / "out"
    rf.main([str(out), "--tsv", str(tmp_path / "f.tsv"), "--stamp", "s"])
    assert (tmp_path / "f.tsv").read_text().splitlines()[1].split("\t")[6] == "unchecked"
