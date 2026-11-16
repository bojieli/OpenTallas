"""QC-CB-GEN-1115: measured cb ring flops per family (not one constant) and gen_cb_strip.py using them."""
import json
from pathlib import Path

import cb_ring_flops as RF

HERE = Path(__file__).resolve().parent


def test_family_values_measured_from_the_kit_logs():
    b = dict(ring_width=576)
    assert RF.ring_flops("cbf_q00_s2", "bc_i00", b) == (2993.0, "measured")
    assert RF.ring_flops("cbn_q11__cl5cc92dfe", "bc_i22", b) == (5426.0, "measured")
    assert RF.ring_flops("cbn_q11__cl5cc92dfe", "na_i22", b) == (5408.0, "measured")
    assert RF.ring_flops("cbn_q01__cld9ff4c40", "rsf_i", b) == (2983.0, "measured")
    assert RF.ring_flops("cbf_q00_s2", "rx_v_serdes_rx_valid_i", dict(ring_width=64)) == (112.0, "measured")


def test_cbx_uses_the_cbn_instance_parameters_and_a00_a22_classes():
    b = dict(ring_width=576)
    assert RF.ring_flops("cbx_q10__cl94a12200", "a22_i", b)[0] == RF.ring_flops("cbn_q01__cld9ff4c40", "a00_i", b)[0] == 5408.0
    assert RF.band_class("a00_i", 576) == "na_i" and RF.band_class("nb_i12", 576) == "nb_i"


def test_synth_over_strip_ratio_is_stable():
    t = json.loads((HERE / "cb_ring_flops.json").read_text())
    s = t["synth_flops"]["cbn_q01__cld9ff4c40"]
    assert abs(s["bc_i02"] / t["strip_flops"]["cbn"]["bc_i"] - 1.022) < 0.01 and abs(s["a00_i"] / t["strip_flops"]["cbn"]["na_i"] - 1.022) < 0.01


def test_unmeasured_flit_serdes_is_scaled_and_labelled():
    f, how = RF.ring_flops("cbf_q00_s2", "rx_flit_serdes_rx_i", dict(ring_width=640))
    assert how == "scaled" and 3000 < f < 3500


def test_measure_netlist_counts_dffs_through_hierarchy(tmp_path):
    v = tmp_path / "n.v"
    v.write_text("module leaf (a);\n  DFFHQNx1_ASAP7_75t_R \\q[0]  (.CLK(c));\n  DFFHQNx1_ASAP7_75t_R \\q[1]  (.CLK(c));\nendmodule\n"
                 "module top (a);\n  leaf  \\u_bound.u_cland_a00_i  (.a(a));\n  leaf  \\u_bound.u_cland_rsf_i  (.a(a));\nendmodule\n")
    assert RF.measure_netlist(v) == {"a00_i": 2, "rsf_i": 2}


def test_gen_cb_strip_reads_the_table_not_a_constant():
    g = (HERE / "gen_cb_strip.py").read_text()
    assert "RF.ring_flops" in g and "FPB" not in g
