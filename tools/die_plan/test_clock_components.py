"""Mixed inverter trees and BUF pads use measured stage delays on both edges."""
import copy
import json
import pytest
import clock_components as C
import die_sta_related as D

B = "BUFx24_ASAP7_75t_R"


def vehicle(tmp_path):
    net = tmp_path / "ctree.v"
    net.write_text(f"module ctree(root,t);\ninput root;\noutput t;\n"
                   f"{C.INV} i0 (.A(root), .Y(n0));\n"
                   f"{B} p0 (.A(n0), .Y(t));\nendmodule\n")
    arr = tmp_path / "arr.txt"
    arr.write_text("# OT_EDGES v1\nN i0 100 90\nM i0 105 95\n"
                   "N p0 120 108\nM p0 135 118\nT t 125 112 1\nF t 141 123\n")
    p = dict(node_cell={"h":"i0", "h0":"p0"}, node_late_ps={"h":100.,"h0":120.},
             node_early_ps={"h":90.,"h0":108.},node_fall_late_ps={"h":105.,"h0":135.},
             node_fall_early_ps={"h":95.,"h0":118.},cppr_node_range_ps={"h":10.,"h0":12.},
             taps=[dict(port="t",late_ps=125.,early_ps=112.,fall_late_ps=141.,fall_early_ps=123.)])
    return p, net, arr


def test_weighted_both_edges_and_nodes(tmp_path):
    raw, net, arr = vehicle(tmp_path)
    a = C.annotate(raw,net,arr)
    assert "clock_components_basis" not in raw
    m,t = D.apply_clock_cal(a,{"t":a["taps"][0]},"TT","inv","spice_edge")
    fs = D.SPICE_CLOCK_CAL_CELL[B]["TT"]
    assert t["t"]["late_ps"] == pytest.approx(100*D.SPICE_CLOCK_CAL_INV["TT"]+25*fs["rise_late"])
    assert t["t"]["fall_late_ps"] == pytest.approx(105*D.SPICE_CLOCK_CAL_INV["TT"]+36*fs["fall_late"])
    assert m["node_late_ps"]["h0"] == pytest.approx(100*.9324+20*fs["rise_late"])
    assert m["cppr_node_range_ps"]["h0"] == round(max(0,m["node_late_ps"]["h0"]-m["node_early_ps"]["h0"]),4)
    # Mutant: using the rise increment for fall fails the independently measured sum.
    bad=copy.deepcopy(a); bad["taps"][0]["clock_components"][0]["fall_late_ps"]-=11
    with pytest.raises(ValueError,match="does not sum"):
        D.apply_clock_cal(bad,{"t":bad["taps"][0]},"TT","inv","spice_edge")


def test_missing_fall_fails_closed(tmp_path):
    p,n,a=vehicle(tmp_path); a.write_text(a.read_text().replace("M p0 135 118\n",""))
    with pytest.raises(ValueError,match="missing measured rise/fall"):
        C.annotate(p,n,a)


def test_legacy_derived_fall_rejected(tmp_path):
    p,n,a=vehicle(tmp_path); a.write_text(a.read_text().replace("# OT_EDGES v1\n", ""))
    with pytest.raises(ValueError,match="OT_EDGES"):
        C.annotate(p,n,a)


def test_stale_proof_and_missing_node_fail(tmp_path):
    p,n,a=vehicle(tmp_path); p["taps"][0]["late_ps"]+=1
    with pytest.raises(ValueError,match="stale tap"):
        C.annotate(p,n,a)
    p,n,a=vehicle(tmp_path); p["node_cell"].pop("h0")
    with pytest.raises(ValueError,match="complete node"):
        C.annotate(p,n,a)


def test_unknown_master_and_missing_decomposition_fail(tmp_path):
    p,n,a=vehicle(tmp_path); p=C.annotate(p,n,a)
    p["taps"][0]["clock_components"][0]["master"]="UNKNOWN"
    with pytest.raises(SystemExit,match="no spice factor"):
        C.apply(p,{"t":p["taps"][0]},"FF","spice_cell")
    p,n,a=vehicle(tmp_path); p=C.annotate(p,n,a); p["node_clock_components"].pop("h0")
    with pytest.raises(ValueError,match="incomplete node"):
        C.apply(p,{"t":p["taps"][0]},"FF","spice_edge")


def test_old_proofs_unchanged_without_optin(tmp_path):
    p,_,_=vehicle(tmp_path); p.pop("node_cell")
    m,t = D.apply_clock_cal(p,{"t":p["taps"][0]},"TT","inv","spice_edge")
    assert t["t"]["late_ps"]==pytest.approx(125*.9324)
    assert "clock_cal_components" not in m
