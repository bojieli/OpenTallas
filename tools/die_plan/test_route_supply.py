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
