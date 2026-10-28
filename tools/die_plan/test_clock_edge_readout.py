"""FLOW-ONEMODEL-2 (COORD 10-28): every die proof carries MEASURED fall arrivals at taps AND tree nodes by
construction: die_trial.clock_edge_readout (T/F per tap, N/M per clock cell, polarity-resolved), trial_tap_arrivals
(F/M rows -> fall_* / node_fall_*), tap_fall_merge --tree (node falls onto an existing proof)."""
import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
import die_sta_related as DSR
import tap_fall_merge as TFM
import trial_tap_arrivals as E
from test_die_trial_link_fishbone import _P, REG, FEED
from test_die_trial_link_htree import TAPS


def _tree():
    return D.build_link_fishbone(_P(), TAPS, REG, FEED, local="htree", leaf_um=200.0)


def _walk_parity(v):
    """independent reference: inverter count root -> each cell output"""
    drv = {m.group(4): (m.group(1), m.group(2), m.group(3))
           for m in re.finditer(r"^\s+(\S+) (\S+) \(\.A\((\S+)\), \.Y\((\S+)\)\);", v, re.M)}
    out = {}
    for net, (cell, inst, a) in drv.items():
        k, n = 0, net
        while n != "root":
            k += "INV" in drv[n][0]
            n = drv[n][2]
        out[inst] = k % 2
    return out


@pytest.mark.parametrize("cc", ["buf", "inv", "inv2"])
def test_parity_matches_netlist_walk_and_taps_true_polarity(cc):
    v = D.tree_netlist(_tree(), TAPS, rep_um=250.0, clock_cell=cc)[0]
    cells, taps = D.clock_parity(v)
    assert cells == _walk_parity(v)
    assert taps and not any(taps.values())          # die_trial: every tap true polarity by construction
    if cc == "buf":
        assert not any(cells.values())
    else:
        assert any(cells.values())                  # inverter trees do have odd outputs (N must read their Y fall)


def test_readout_polarity_resolved_rows():
    v = D.tree_netlist(_tree(), TAPS, rep_um=250.0, clock_cell="inv")[0]
    cells, _ = D.clock_parity(v)
    odd = {c for c, p in cells.items() if p}
    t = "\n".join(D.clock_edge_readout(v, "/out/arr.txt", period="833.0", cells="ck_*", tap_slew=True, prefix="ck_"))
    d = re.search(r"set ot_odd \[dict create([^\]]*)\]", t).group(1).split()[0::2]
    assert set(d) == {"ck_" + c for c in odd}
    assert D.EDGES_HDR in t
    assert "F [get_full_name $p] [expr {833.0 - [get_property $p slack_max_fall]}] [get_property $p slack_min_fall]" \
           " [get_property $p slew_max_fall]" in t
    assert "set e fall; set g rise } else { set e rise; set g fall }" in t
    assert 'N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$e]' in t
    assert 'M [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$g]' in t


def test_readout_refuses_inverted_tap():
    v = "module ctree (root, t_a);\n  input root;\n  output t_a;\n  wire n0;\n" \
        "  CKINVDCx16_ASAP7_75t_R b0 (.A(root), .Y(n0));\n  assign t_a = n0;\nendmodule\n"
    with pytest.raises(ValueError, match="inverted polarity"):
        D.clock_edge_readout(v, "x")


def _nodes():
    return {0: dict(x=10., y=10., parent=None, level=0, kids=[1], region_root=None, taps=[]),
            1: dict(x=60., y=10., parent=0, level=1, kids=[], region_root="A",
                    taps=[("part", "ck", 70., 60.), ("part", "ck2", 80., 60.)])}


def _kit(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "clock_taps", lambda p: [])
    monkeypatch.setattr(D, "build_htree", lambda *a, **k: copy.deepcopy(_nodes()))
    out = tmp_path / "clock"
    D.clock_kit(SimpleNamespace(W=100., H=100.), out, 100., 450.)
    return out


def test_clock_kit_ctree_tcl_emits_both_edges(tmp_path, monkeypatch):
    out = _kit(tmp_path, monkeypatch)
    t = (out / "ctree.tcl").read_text()
    assert "set fh [open /work/clock/arr_$::env(CORNER).txt w]" in t and D.EDGES_HDR in t
    assert "puts $fh \"T $n [expr {833.333 - $smx}] [expr {$smn}]\" }" in t      # T row unchanged
    assert "slack_max_fall" in t and "\"M [get_full_name $i]" in t and "foreach i [get_cells b*]" in t


def _arr(tree, path, fall_shift=40.0, node_fall=True, header=True, legacy_qc=False):
    rows = [D.EDGES_HDR + " test"] if header else []
    for i, cell in enumerate(sorted({str(v) for v in tree["node_buf"].values()})):
        rows.append(f"N {cell} {10 + i} {9 + i}")
        if node_fall:
            rows.append(f"M {cell} {10 + i + fall_shift} {9 + i + fall_shift - 3}")
    for x in tree["taps"]:
        rows.append(f"T {x['port']} 100 90 20")
        rows.append(f"F {x['port']} 140 120 22" if legacy_qc else f"F {x['port']} {100 + fall_shift} {90 + fall_shift - 5} 21")
    path.write_text("\n".join(rows) + "\n")
    return path


def test_trial_tap_arrivals_emits_tap_and_node_falls(tmp_path, monkeypatch):
    out = _kit(tmp_path, monkeypatch)
    tree = json.loads((out / "tree.json").read_text())
    r, miss = E.export(out / "tree.json", _arr(tree, tmp_path / "a.txt"), "TT")
    assert miss == 0
    assert all(t["fall_late_ps"] == 140.0 and t["fall_early_ps"] == 125.0 for t in r["taps"])
    assert set(r["node_fall_late_ps"]) == set(r["node_late_ps"])           # EVERY node key, incl region + 'h'
    for k in r["node_late_ps"]:
        assert r["node_fall_late_ps"][k] == r["node_late_ps"][k] + 40.0
        assert r["node_fall_early_ps"][k] == r["node_early_ps"][k] + 37.0
    assert r["fall_arrivals"]["nodes_with_fall"] == len(r["node_late_ps"])
    # a start retime flop on a tree node now has a measured fall arrival (no fail-closed for want of data)
    taps = {t["port"]: t for t in r["taps"]}
    k = DSR.virtual_tap(r, taps, "h", (5.0, 4.0, 1), (6.0, 5.0, 1))
    assert taps[k]["fall_late_ps"] == r["node_fall_late_ps"]["h"] + 6.0


def test_trial_tap_arrivals_rise_only_and_legacy_forms(tmp_path, monkeypatch):
    out = _kit(tmp_path, monkeypatch)
    tree = json.loads((out / "tree.json").read_text())
    p = tmp_path / "r.txt"
    p.write_text("\n".join(ln for ln in _arr(tree, tmp_path / "x.txt").read_text().splitlines()
                           if ln[:1] in ("T", "N")) + "\n")
    r, _ = E.export(out / "tree.json", p, "TT")
    assert "node_fall_late_ps" not in r and "fall_arrivals" not in r
    assert not any("fall_late_ps" in t for t in r["taps"])                   # rise-only file: output unchanged
    # DIE-QC-11 legacy 'F port fall_late rise_late slew' (no header): fall - rise delta on the T row
    r, _ = E.export(out / "tree.json", _arr(tree, tmp_path / "q.txt", header=False, node_fall=False, legacy_qc=True), "TT")
    assert all(t["fall_late_ps"] == 140.0 and t["fall_early_ps"] == 90.0 + 20.0 for t in r["taps"])


def test_tap_fall_merge_tree_adds_node_falls(tmp_path, monkeypatch):
    out = _kit(tmp_path, monkeypatch)
    tree = json.loads((out / "tree.json").read_text())
    arr = _arr(tree, tmp_path / "a.txt")
    rise = tmp_path / "rise.txt"
    rise.write_text("\n".join(ln for ln in arr.read_text().splitlines() if ln[:1] in ("T", "N")) + "\n")
    proof = tmp_path / "proof"
    proof.mkdir()
    r, _ = E.export(out / "tree.json", rise, "TT")
    for t in r["taps"]:                                                       # a scaled proof (spice cal etc.)
        t["late_ps"] += 7.0
    (proof / "tap_arrivals_TT.json").write_text(json.dumps(r))
    assert TFM.main([str(proof), "TT", str(arr), "--out", str(tmp_path / "pf"), "--tree", str(out / "tree.json")]) == 0
    m = json.loads((tmp_path / "pf" / "tap_arrivals_TT.json").read_text())
    assert m["fall_arrivals"]["nodes_with_fall"] == len(m["node_late_ps"]) > 0
    for k in m["node_late_ps"]:
        assert m["node_fall_late_ps"][k] == m["node_late_ps"][k] + 40.0
    assert all(t["fall_late_ps"] == t["late_ps"] + 40.0 and t["fall_early_ps"] == t["early_ps"] + 35.0
               for t in m["taps"])
    # header file without --tree: tap deltas from T/F (never misread as the legacy fall/rise form)
    assert TFM.main([str(proof), "TT", str(arr), "--out", str(tmp_path / "pg")]) == 0
    g = json.loads((tmp_path / "pg" / "tap_arrivals_TT.json").read_text())
    assert all(t["fall_late_ps"] == t["late_ps"] + 40.0 for t in g["taps"]) and "node_fall_late_ps" not in g


def test_tap_fall_merge_tree_resolves_node_cell_keys_and_fails_closed_on_low_coverage(tmp_path, monkeypatch):
    """FLOW-ONEMODEL-4 (DIE-HEAD-12: 1/2229 nodes merged): a DIE-HEAD mk_proof --tree-path proof keys its nodes by
    U+0100 child-index paths + region names and carries node_cell {key: clock cell}; the merge resolves through that
    map.  Keys that resolve to nothing (< 95 % of nodes) fail closed and leave no output proof."""
    out = _kit(tmp_path, monkeypatch)
    tree = json.loads((out / "tree.json").read_text())
    arr = _arr(tree, tmp_path / "a.txt")
    cells = sorted({str(v) for v in tree["node_buf"].values()})
    rise = tmp_path / "rise.txt"
    rise.write_text("\n".join(ln for ln in arr.read_text().splitlines() if ln[:1] in ("T", "N")) + "\n")
    r, _ = E.export(out / "tree.json", rise, "TT")
    key_cell = {k: cells[int(v) - 10] for k, v in r["node_late_ps"].items()}      # N late = 10 + cell index
    ren = {k: "h" + "".join(chr(0x100 + CH_I) for CH_I in range(len(k) - 1)) + f"#{i}" if k.startswith("h") else k
           for i, k in enumerate(r["node_late_ps"])}
    for f in ("node_late_ps", "node_early_ps", "node_stages", "node_xy_um", "cppr_node_range_ps"):
        r[f] = {ren[k]: v for k, v in r[f].items()}
    r["node_cell"] = {ren[k]: c for k, c in key_cell.items()}
    proof = tmp_path / "proof"
    proof.mkdir()
    (proof / "tap_arrivals_TT.json").write_text(json.dumps(r))
    assert TFM.main([str(proof), "TT", str(arr), "--out", str(tmp_path / "pf"), "--tree", str(out / "tree.json")]) == 0
    m = json.loads((tmp_path / "pf" / "tap_arrivals_TT.json").read_text())
    fa = m["fall_arrivals"]
    assert fa["nodes_with_fall"] == fa["nodes"] == len(r["node_late_ps"]) and fa["node_match"]["node_cell"] == fa["nodes"]
    for k in m["node_late_ps"]:
        assert m["node_fall_late_ps"][k] == m["node_late_ps"][k] + 40.0
        assert m["node_fall_early_ps"][k] == m["node_early_ps"][k] + 37.0
    # the same proof without node_cell: keys match nothing in the export -> fail closed, no proof written
    r.pop("node_cell")
    (proof / "tap_arrivals_TT.json").write_text(json.dumps(r))
    assert TFM.main([str(proof), "TT", str(arr), "--out", str(tmp_path / "pz"), "--tree", str(out / "tree.json")]) == 2
    assert not (tmp_path / "pz" / "tap_arrivals_TT.json").exists()
    with pytest.raises(TFM.NodeCoverageError):
        TFM.merge_tree(r, out / "tree.json", arr, "TT")
