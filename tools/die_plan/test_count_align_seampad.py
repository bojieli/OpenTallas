"""KV-CROSSING-1119 (COORD 11-20): count_align_plan seam-group / pad-strap rules for a fall-aware re-plan.
(a) the members of a seam group keep ONE common latency (the max); (b) no lane is shortened past its pad-strap headroom."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402

T, AP = 833.0, 833.0 / 8


def xing(port, lat, kind="nontree", k=0, lo=700.0, hi=1100.0, depth=4):
    return dict(port=port, src="a", dst="b", kind=kind, K=k, K_eff=k, lat_cycles=lat, rx_lat_counts=lat - 1,
                L_lo_ps=lo, L_hi_ps=hi, depth=depth, margin_lo_ps=lo - T / 2, margin_hi_ps=(depth - 0.5) * T - hi,
                rtl=dict(module="ot_dp_clk_landing_ca", DEPTH=depth, K=k, GUARD_LO=0, GUARD_HI=depth))


def plan_doc(groups, lanes, base):
    return dict(latency_groups=[dict(name=f"g{i}", kind="replica", lanes=g) for i, g in enumerate(groups)],
                latency=dict(lanes={k: dict(pad=v) for k, v in lanes.items()}),
                clock=dict(landing_network=dict(count_aligned_cycles=base)))


def test_inputs_read_groups_and_pad_floor():
    d = plan_doc([["L1", "L2"]], {"L1": 0, "L2": 12, "L3": 0}, {"L1_0": 5, "L2_0": 5, "L2_1": 5, "L3_0": 4})
    g, f = CAP.seam_pad_inputs(d)
    assert g == [["L1_0", "L2_0", "L2_1"]]
    assert f["L1_0"] == 5 - 15 and f["L2_0"] == 5 - 3 and f["L3_0"] == 4 - 15


def test_group_takes_the_max_and_depth_follows():
    # one member shifted by 3, the other by 4 (QC CS_RXV): both end on the larger latency
    out = [xing("L1_0", 8, hi=2200.0, depth=4), xing("L2_0", 9, hi=2200.0, depth=4)]
    s = CAP.seam_pad_rules(out, [["L1_0", "L2_0"]], {}, T, AP, 8)
    assert out[0]["lat_cycles"] == out[1]["lat_cycles"] == 9 and s["raised"] == 1 and s["raised_cycles"] == 1
    assert out[0]["K"] == 1 and out[0]["rtl"]["K"] == 1 and out[0]["rx_lat_counts"] == 8
    assert out[0]["L_hi_ps"] == 2200.0 + T and out[0]["depth"] == 8 and s["depth_promoted"] == 1
    assert out[0]["margin_hi_ps"] == round(7.5 * T - 2200.0 - T, 1)
    assert out[1]["K"] == 0                      # the longer member is untouched


def test_pad_strap_floor_never_shortens_past_capacity():
    out = [xing("L3_0", 20)]
    s = CAP.seam_pad_rules(out, [], {"L3_0": 25}, T, AP, 8)         # declared 40, pad 0 of 15 -> floor 25 > planned 20
    assert out[0]["lat_cycles"] == 25 and s["raised"] == 1


def test_tree_crossing_is_reported_not_edited():
    out = [xing("L1_0", 8, kind="tree"), xing("L2_0", 9)]
    s = CAP.seam_pad_rules(out, [["L1_0", "L2_0"]], {}, T, AP, 8)
    assert out[0]["lat_cycles"] == 8 and s["skipped_tree"] == ["L1_0"]


def test_no_groups_no_change():
    out = [xing("L1_0", 8), xing("L2_0", 9)]
    before = [dict(o) for o in out]
    CAP.seam_pad_rules(out, [], {}, T, AP, 8)
    assert out == before


def test_qc_port_names_map_to_their_own_lane():
    # QC ports are <lane>__<k>; lane names hold '_' and '__'.  Only the grouped lanes may form a group, and the pad
    # floor reads the port's own lane (not one lane 'sl' for every sl_* port).
    d = plan_doc([["sl_E0_su_l0__x_su_l0_ctl", "sl_E0_su_l1__x_su_l1_ctl"]],
                 {"sl_E0_su_l0__x_su_l0_ctl": 0, "sl_E0_su_l1__x_su_l1_ctl": 0, "sl_E2_hc2__cws2": 9},
                 {"sl_E0_su_l0__x_su_l0_ctl__0": 5, "sl_E0_su_l1__x_su_l1_ctl__1": 6, "sl_E2_hc2__cws2__3": 3,
                  "glue__native_rx_v_native_rx_v__0": 2})
    g, f = CAP.seam_pad_inputs(d)
    assert g == [["sl_E0_su_l0__x_su_l0_ctl__0", "sl_E0_su_l1__x_su_l1_ctl__1"]]
    assert f["sl_E2_hc2__cws2__3"] == 3 - (15 - 9) and f["glue__native_rx_v_native_rx_v__0"] == 2 - 15
