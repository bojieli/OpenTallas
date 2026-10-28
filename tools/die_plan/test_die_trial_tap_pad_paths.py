"""Actual multiple-tap pad identity, site and propagated timing-path controls."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
import die_trial as D
import trial_tap_arrivals as E


def nodes():
    return {0: dict(x=10., y=10., parent=None, level=0, kids=[], region_root="A",
                    taps=[("part", "ck", 70., 60.), ("part", "ck2", 80., 60.)])}


def test_same_part_same_leaf_pad_identity_and_parent_chain():
    n = nodes()
    pads = {"t_part__ck": 2, "t_part__ck2": 3}
    v, place, taps, nb, po = D.tree_netlist(n, [], tap_pad=pads)
    names = [r[0] for r in place]
    assert len(names) == len(set(names)) == 6
    assert po["p0_t_part__ck_0"] == "b0"
    assert po["p0_t_part__ck_1"] == "p0_t_part__ck_0"
    assert po["p0_t_part__ck2_2"] == "p0_t_part__ck2_1"
    assert "assign t_part__ck = pn0_t_part__ck_1;" in v
    assert "assign t_part__ck2 = pn0_t_part__ck2_2;" in v
    assert D.tree_netlist(n, []) == D.tree_netlist(n, [], tap_pad={})


def test_explicit_pad_bays_used_without_slide_and_invalid_bays_rejected():
    class Site:
        def legal(self, q): return q[0] < 50
        def nearest(self, q): raise AssertionError("explicit bay must not slide")
    pads = {"t_part__ck": 2}
    bays = {"t_part__ck": [[20., 20.], [30., 20.]]}
    _, place, *_ = D.tree_netlist(nodes(), [], site=Site(), tap_pad=pads, tap_pad_sites=bays)
    assert place[-2:] == [("p0_t_part__ck_0", 20., 20.), ("p0_t_part__ck_1", 30., 20.)]
    with pytest.raises(ValueError, match="not legal"):
        D.tree_netlist(nodes(), [], site=Site(), tap_pad=pads, tap_pad_sites={"t_part__ck": [[20.,20.],[60.,20.]]})
    with pytest.raises(ValueError, match="count"):
        D.tree_netlist(nodes(), [], tap_pad=pads, tap_pad_sites={"t_part__ck": [[20.,20.]]})


def test_pad_metadata_and_actual_arrival_export(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "clock_taps", lambda p: [])
    monkeypatch.setattr(D, "build_htree", lambda *a, **k: copy.deepcopy(nodes()))
    out = tmp_path/"clock"
    D.clock_kit(SimpleNamespace(W=100., H=100.), out, 100., 450.,
                tap_pad={"t_part__ck": 2, "t_part__ck2": 1,
                         "sites": {"t_part__ck": [[20.,20.],[30.,20.]], "t_part__ck2": [[40.,20.]]}})
    t = json.loads((out/"tree.json").read_text())
    a, b = t["taps"]
    assert a["driver"] == "p0_t_part__ck_1"
    assert a["path"] == ["b0", "p0_t_part__ck_0", "p0_t_part__ck_1"]
    assert a["stages_from_root"] == 3
    assert t["sites"][a["driver"]] == [30.,20.]
    assert "get_cells {b* r* p*}" in (out/"ctree.tcl").read_text()
    assert "[expr {$smn}] [get_property $p slew_max_rise]" in (out/"ctree.tcl").read_text()
    arr = tmp_path/"arr_TT.txt"
    arr.write_text("\n".join([f"N {cell} {10+i} {9+i}" for i, cell in enumerate(t["sites"])] +
                            [f"T {x['port']} 100 90 20" for x in t["taps"]])+"\n")
    result, missing = E.export(out/"tree.json", arr, "TT")
    assert missing == 0
    a, b = result["taps"]
    assert a["stages_from_root"] == 4 and b["stages_from_root"] == 3
    assert a["cppr_node"] == b["cppr_node"] == "A"
    assert os.path.commonprefix([a["tree_path"], b["tree_path"]]) == "h"
    assert result["node_stages"][a["tree_path"]] == 3
    assert result["node_late_ps"]["A"] == 10
    arr.write_text("\n".join(l for l in arr.read_text().splitlines() if not l.startswith("N p"))+"\n")
    with pytest.raises(ValueError, match="missing N"):
        E.export(out/"tree.json", arr, "TT")


def test_actual_cli_preserves_body_packer_sibling_sites(tmp_path, monkeypatch):
    path = tmp_path/"tap_pad_bays.json"
    raw = dict(pad={"t_part__ck": 2}, sites={"t_part__ck": [[20.,20.],[30.,20.]]})
    path.write_text(json.dumps(raw))
    captured = {}
    def write(*args, **kwargs):
        captured.update(kwargs)
        return dict.fromkeys(("die","parts","types","closed_views","hard_cores","clock_tree","grt","psm","sta"))
    monkeypatch.setattr(D, "write_kit", write)
    D.main(["kit", "unused_plan.json", "--out", str(tmp_path/"kit"), "--tap-pad", str(path)])
    assert captured["tap_pad"] == {"t_part__ck": 2, "sites": raw["sites"]}
    # Existing counts-only envelope and direct function input stay unchanged.
    path.write_text(json.dumps(dict(pad=raw["pad"], source="old metadata")))
    assert D.load_tap_pad(path) == raw["pad"]
