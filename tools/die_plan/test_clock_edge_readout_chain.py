"""R-CLOCK-6 (g) (HOLD-TAP-1 11-13): every die-clock gate chain writes BOTH source edges of the routed clock.
mk_combo_kv.py (die_trial region trees, inv / inv2), die_clock.sta_tcl + dieclock_arrivals.py (die_clock BUFx24 trees)."""
import json
from pathlib import Path
import die_clock
import die_trial
import dieclock_arrivals as DA
import mk_combo_kv as MK
import trial_tap_arrivals as TTA

INV2 = """module ctree (root, t_a__clk, t_b__clk);
  input root;
  output t_a__clk;
  output t_b__clk;
  wire w0;
  wire w1;
  wire w2;
  CKINVDCx16_ASAP7_75t_R b0 (.A(root), .Y(w0));
  CKINVDCx16_ASAP7_75t_R b1 (.A(w0), .Y(w1));
  CKINVDCx16_ASAP7_75t_R b2 (.A(w1), .Y(w2));
  CKINVDCx16_ASAP7_75t_R b3 (.A(w2), .Y(t_a__clk));
  CKINVDCx16_ASAP7_75t_R b4 (.A(w2), .Y(t_b__clk));
endmodule
"""


def test_headers_agree():
    assert die_clock.EDGES_HDR == die_trial.EDGES_HDR == TTA.EDGES_HDR == DA.EDGES_HDR


def test_combo_readout_is_both_edge_and_polarity_resolved():
    t = MK.readout_tcl(INV2, rise_only=False)
    assert die_trial.EDGES_HDR in t
    for row in ('puts $fh "T ', 'puts $fh "F ', 'puts $fh "N ', 'puts $fh "M '):
        assert row in t, row
    assert "slack_max_fall" in t and "slack_min_fall" in t
    # odd-parity cells (1st and 3rd inverter of the chain) are listed with the ck_ prefix of the combined design
    odd = t.split("\n")[0]
    assert odd.startswith("set ot_odd [dict create") and " ck_b0 1" in odd and " ck_b2 1" in odd
    assert " ck_b1 1" not in odd and " ck_b3 1" not in odd
    # node rows take the edge by parity, never a fixed arrival_max_rise
    assert "arrival_max_$e" in t and "arrival_max_$g" in t and "[get_property $q arrival_max_rise]" not in t
    assert "/out/arr_$::env(CORNER).txt" in t and "string range [get_full_name $i] 3 end" in t


def test_combo_rise_only_is_the_old_form_and_opt_in(monkeypatch):
    t = MK.readout_tcl(INV2, rise_only=True)
    assert 'puts $fh "F ' not in t and 'puts $fh "M ' not in t and "[get_property $q arrival_max_rise]" in t
    monkeypatch.delenv("OT_COMBO_RISE_ONLY", raising=False)
    assert 'puts $fh "F ' in MK.readout_tcl(INV2)
    monkeypatch.setenv("OT_COMBO_RISE_ONLY", "1")
    assert 'puts $fh "F ' not in MK.readout_tcl(INV2)


def test_combo_script_end_to_end(tmp_path, monkeypatch):
    k, c, o = tmp_path / "kit", tmp_path / "clk", tmp_path / "out"
    (k / "grt").mkdir(parents=True); c.mkdir()
    (k / "grt" / "route.v").write_text("module die_route (p0);\n  input p0;\nendmodule\n")
    (k / "grt" / "grt.tcl").write_text("set t0 [clock seconds]\nread_verilog /work/grt/route.v\nlink_design die_route\n"
                                       "source /work/grt/obs.tcl\nglobal_route\n")
    (c / "ctree.v").write_text(INV2)
    (c / "ctree_ck89.tcl").write_text("place_pin -pin_name root -layer M9 -location {0 0}\nplace_inst -name b0 -location {1 1}\n")
    monkeypatch.setenv("ADJ", "0.75"); monkeypatch.setenv("CORNER", "TT"); monkeypatch.delenv("OT_COMBO_RISE_ONLY", raising=False)
    assert MK.main(["mk_combo_kv.py", str(k), str(c), str(o)]) == 0
    tcl = (o / "combo.tcl").read_text()
    assert die_trial.EDGES_HDR in tcl and tcl.count("close $fh") == 1 and tcl.rstrip().endswith("puts OT_DONE")
    assert "place_inst -name ck_b0" in tcl and "link_design die_combo" in tcl
    assert "create_clock -name dck -period 833.0" in tcl and "create_clock -name vclk -period 833.0" in tcl
    assert "833.333" not in tcl
    assert tcl.index("read_liberty") < tcl.index("link_design die_combo")
    v = (o / "combo.v").read_text()
    assert "CKINVDCx16_ASAP7_75t_R ck_b3 (.A(ck_w2), .Y(t_a__clk));" in v


def test_die_clock_sta_writes_fall_rows_and_keeps_rise_rows(tmp_path):
    t = die_clock.sta_tcl(tmp_path, "TT", "/lib")
    assert die_clock.EDGES_HDR in t
    # the rise rows are byte-identical to the rise-only form
    assert ('foreach p [get_ports t_*] { puts $fh "T [get_full_name $p] [expr {' + str(die_clock.PERIOD_PS)
            + ' - [get_property $p slack_max_rise]}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]" }') in t
    assert 'puts $fh "N [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]"' in t
    assert 'puts $fh "F [get_full_name $p] [expr {' in t and "slack_max_fall" in t
    assert 'puts $fh "M [get_full_name $i] [get_property $q arrival_max_fall] [get_property $q arrival_min_fall]"' in t


ARR = """# OT_EDGES v1 T/N=source rise F/M=source fall (late early)
T t_a__clk 300.0 290.0 20.0
T t_b__clk 310.0 300.0 21.0
F t_a__clk 410.0 400.0 22.0
F t_b__clk 425.0 415.0 23.0
N tr0 50.0 49.0
M tr0 80.0 79.0
N n0_0 100.0 98.0
M n0_0 150.0 148.0
"""
TREE = {"taps": [{"port": "t_a__clk", "part": "a", "xy": [0, 0], "leaf": "n0_0", "path": ["tr0", "n0_0"]},
                 {"port": "t_b__clk", "part": "b", "xy": [1, 1], "leaf": "n0_0", "path": ["tr0", "n0_0"]}]}


def _run(tmp_path, arr):
    (tmp_path / "tree.json").write_text(json.dumps(TREE)); (tmp_path / "arr_TT.txt").write_text(arr)
    return DA.export(tmp_path, "TT")


def test_dieclock_arrivals_carries_fall(tmp_path):
    res, miss = _run(tmp_path, ARR)
    assert miss == 0
    a = {t["port"]: t for t in res["taps"]}
    assert (a["t_a__clk"]["late_ps"], a["t_a__clk"]["early_ps"]) == (300.0, 290.0)          # rise unchanged
    assert (a["t_a__clk"]["fall_late_ps"], a["t_a__clk"]["fall_early_ps"]) == (410.0, 400.0)
    assert a["t_b__clk"]["fall_late_ps"] - a["t_b__clk"]["late_ps"] == 115.0                # the measured duty shift
    assert res["node_fall_late_ps"]["h"] == 80.0 and len(res["node_fall_late_ps"]) == len(res["node_late_ps"])
    assert res["fall_arrivals"]["taps_with_fall"] == 2


def test_dieclock_arrivals_rise_only_file_is_unchanged(tmp_path):
    rise = "\n".join(ln for ln in ARR.splitlines() if ln[0] in "TN") + "\n"
    res, _ = _run(tmp_path, rise)
    assert all("fall_late_ps" not in t for t in res["taps"]) and "node_fall_late_ps" not in res and "fall_arrivals" not in res
    # a headerless F row is the legacy 'F port fall rise' form: never read as late / early
    res2, _ = _run(tmp_path, rise + "F t_a__clk 410.0 300.0 22.0\n")
    assert all("fall_late_ps" not in t for t in res2["taps"])


def test_legacy_readers_ignore_the_new_rows(tmp_path):
    f = tmp_path / "arr_TT.txt"; f.write_text(ARR)
    tarr, tmin, slew, narr = die_clock.read_arr(f)
    assert tarr == {"t_a__clk": 300.0, "t_b__clk": 310.0} and narr == {"tr0": 50.0, "n0_0": 100.0}
    assert die_clock.read_node_ranges(f) == {"tr0": (50.0, 49.0), "n0_0": (100.0, 98.0)}
    T, N = DA.read_arr(f)
    assert set(T) == {"t_a__clk", "t_b__clk"} and set(N) == {"tr0", "n0_0"}
