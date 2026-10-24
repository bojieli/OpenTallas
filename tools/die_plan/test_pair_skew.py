"""pair_skew.py (owner gate 10-23): related flop-pair skew with CPPR <= 80 ps at TT and FF, intra + seam; spread is
information only.   python3 -m pytest -q tools/die_plan/test_pair_skew.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pair_skew as PS  # noqa: E402


def tsv(tmp, name, corner, pairs, ck=(), scope=None):
    L = [f"H\tcorner\t{corner}", "H\twns_ps\t-10.5", "H\ttns_ps\t-20.0", "H\twhs_ps\t3.0", "H\tths_ps\t0.00"]
    if scope:
        L.append(f"H\tscope\t{scope}")
    L += [f"P\t{d}\t{a}\t{b}\t{s}\t100.0\t1.5" for d, a, b, s in pairs]
    L += [f"C\t{i}\t{a}\t{f}" for i, a, f in ck]
    p = tmp / name
    p.write_text("\n".join(L) + "\n")
    return p


DIE = [("max", "pA/u_x.q[0]", "pA/u_y.q[0]", -40.0), ("min", "pA/u_x.q[0]", "pA/u_y.q[0]", 55.0),
       ("max", "pA/u_o.q[1]", "pB/u_i.q[1]", 70.0), ("min", "pB/u_o.q[2]", "pA/u_i.q[2]", -60.0)]
# CK spread 150 ps (> 80) but every pair <= 80
CK = [("pA/u_x.q[0]", 100.0, 1), ("pA/u_y.q[0]", 250.0, 1), ("pB/u_i.q[1]", 180.0, 0)]


def test_classification_and_stats(tmp_path):
    s = PS.summarize(PS.read_tsv(tsv(tmp_path, "t.tsv", "TT", DIE, CK)))
    assert s["scope"] == "die"
    intra, seam = s["classes"]["intra"], s["classes"]["seam"]
    assert intra["setup"]["n"] == 1 and intra["hold"]["worst_signed_ps"] == 55.0
    assert intra["all"]["worst_abs_ps"] == 55.0
    assert seam["all"]["n"] == 2 and seam["all"]["worst_signed_ps"] == 70.0
    assert seam["hold"]["worst_signed_ps"] == -60.0
    assert list(s["seams"]) == ["pA|pB"] and s["seams"]["pA|pB"]["worst_abs_ps"] == 70.0
    assert s["spread_all"]["spread_ps"] == 150.0 and s["spread_face"]["spread_ps"] == 150.0
    assert s["spread_face"]["n"] == 2
    assert s["signoff"] == {"wns_ps": -10.5, "tns_ps": -20.0, "whs_ps": 3.0, "ths_ps": 0.0}


def test_p99():
    rows = [("max", "a", "b", float(i)) for i in range(1, 201)]
    rows = [(d, a, b, s, 0.0, 0.0) for d, a, b, s in rows]
    st = PS._stats(rows)
    assert st["worst_abs_ps"] == 200.0 and st["p99_abs_ps"] == 198.0


def test_spread_over_80_pairs_under_80_passes(tmp_path):
    s = PS.summarize(PS.read_tsv(tsv(tmp_path, "t.tsv", "TT", DIE, CK)))
    g = PS.gate([s])
    assert g["verdict"] == "PASS" and s["spread_all"]["spread_ps"] > 80
    assert "FF not measured" in g["notes"]


def test_seam_pair_85_fails(tmp_path):
    rows = DIE + [("min", "pA/u_o.q[3]", "pB/u_i.q[3]", 85.0)]
    s = PS.summarize(PS.read_tsv(tsv(tmp_path, "t.tsv", "FF", rows)))
    g = PS.gate([s])
    assert g["verdict"] == "FAIL" and "FF seam" in g["fails"][0] and g["worst_abs_ps"]["FF_seam"] == 85.0
    assert g["worst_abs_ps"]["FF_intra"] == 55.0


def test_tt_ff_combined(tmp_path):
    tt = PS.summarize(PS.read_tsv(tsv(tmp_path, "tt.tsv", "TT", DIE)))
    ff = PS.summarize(PS.read_tsv(tsv(tmp_path, "ff.tsv", "FF", DIE[:2] + [("max", "pA/a", "pA/b", -80.5)])))
    g = PS.gate([tt, ff])
    assert g["verdict"] == "FAIL" and len(g["fails"]) == 1 and g["fails"][0].startswith("FF intra")
    assert g["notes"] == []
    assert PS.gate([tt, PS.summarize(PS.read_tsv(tsv(tmp_path, "ff2.tsv", "FF", DIE)))])["verdict"] == "PASS"
    assert PS.gate([tt], limit=60)["verdict"] == "FAIL"


def test_kit_scope_all_intra(tmp_path):
    rows = [("max", "u_a/x", "u_b/y", 30.0), ("min", "u_c/x", "u_a/y", -20.0)]
    s = PS.summarize(PS.read_tsv(tsv(tmp_path, "k.tsv", "TT", rows, scope="kit")))
    assert list(s["classes"]) == ["intra"] and s["classes"]["intra"]["all"]["n"] == 2 and not s["seams"]


def test_seam_map_merges_instances(tmp_path):
    s = PS.summarize(PS.read_tsv(tsv(tmp_path, "t.tsv", "TT", DIE)), seam_map={"pA": "P", "pB": "P"})
    assert list(s["classes"]) == ["intra"]


def test_no_pairs(tmp_path):
    s = PS.summarize(PS.read_tsv(tsv(tmp_path, "t.tsv", "TT", [])))
    assert PS.gate([s])["verdict"] == "NO_DATA"


def test_cli_gate_exit_and_json(tmp_path):
    a = tsv(tmp_path, "tt.tsv", "TT", DIE)
    b = tsv(tmp_path, "ff.tsv", "FF", DIE + [("max", "pA/a", "pB/b", 81.0)])
    out = tmp_path / "g.json"
    assert PS.main(["gate", str(a), "--json", str(out)]) == 0
    assert PS.main(["gate", str(a), str(b), "--json", str(out)]) == 1
    assert json.loads(out.read_text())["gate"]["verdict"] == "FAIL"
    assert PS.main(["summarize", str(a), str(b)]) == 0          # summarize never fails


def test_wrappers():
    t = PS.kit_tcl("/k/4_cts.odb", "/k/4_cts.sdc")
    assert "read_db /k/4_cts.odb" in t and "estimate_parasitics -global_routing" in t and "*SRAM*" in t
    assert "OT_PS_SCOPE) kit" in t and t.rstrip().endswith("source /t/pair_skew.tcl")
    assert "read_spef /k/6.spef" in PS.kit_tcl("/k/a.odb", "/k/a.sdc", spef="/k/6.spef")
    assert "PAIRSKEW_OUT" in PS.die_tcl() and "pair_skew.tcl" in PS.die_tcl()
