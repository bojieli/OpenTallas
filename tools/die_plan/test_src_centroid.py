"""tests of src_centroid.py and its use by routed_reach / leg405_perbit (C-LEG405 SRC-NOT-AT-LEAF)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leg405_perbit as LB  # noqa: E402
import routed_reach as RR  # noqa: E402
import src_centroid as SC  # noqa: E402


def geom(tmp_path):
    # out bus x_o: source regs 1,2 at x=1100 -> inverter 3 -> station 0 regs 10,11 at x=500 (hop 600 / 560), station 1 reg 12; in bus y_i: last station 20 -> consumer 30
    rows = [("C", 1, "S", "DFF", 1100, 500, 1100.1, 500.1, "u_bound.g_core_procdff_1_q\\[0\\]$_DFF_P_"),
            ("C", 2, "S", "DFF", 1060, 500, 1060.1, 500.1, "u_bound.g_core_procdff_1_q\\[1\\]$_DFF_P_"),
            ("C", 3, "B", "INV", 800, 500, 800.1, 500.1, "u_bound.inv3"),
            ("C", 10, "S", "DFF", 500, 500, 500.1, 500.1, "u_bound.u_ist_x_o_0/q0$_DFF_P_"),
            ("C", 11, "S", "DFF", 500, 540, 500.1, 540.1, "u_bound.u_ist_x_o_0/q1$_DFF_P_"),
            ("C", 12, "S", "DFF", 300, 500, 300.1, 500.1, "u_bound.u_ist_x_o_1/q0$_DFF_P_"),
            ("C", 20, "S", "DFF", 100, 100, 100.1, 100.1, "u_bound.u_ist_y_i_0/q0$_DFF_P_"),
            ("C", 30, "S", "DFF", 700, 100, 700.1, 100.1, "u_bound.g_cons_q$_DFF_P_"),
            ("C", 40, "S", "DFF", 5, 5, 5.1, 5.1, "u_bound.u_rst_relay_0")]
    nets = [("N", "n1", "i1", "i3"), ("N", "n3", "i3", "i10"), ("N", "n2", "i2", "i11"), ("N", "n4", "i20", "i30"), ("N", "nr", "i40", "i10")]
    p = tmp_path / "geom.tsv"
    p.write_text("\n".join("\t".join(str(x) for x in r) for r in rows + nets) + "\n")
    return str(p)


def test_out_bus_hop_starts_at_the_source_register_not_leaf(tmp_path):
    g = SC.load(geom(tmp_path))
    r = SC.source_chain(g, "x_o", True)
    assert r["stations"] == 2 and r["n_edges"] == 2          # reset relay net into station 0 is not a source
    assert abs(r["max_um"] - 600.0) < 0.3 and r["n_over"] == 2 and "procdff" in r["worst"][0][1]
    assert abs(r["src_centroid"][0] - 1080.0) < 0.2 and abs(r["src_centroid"][1] - 500.0) < 0.2


def test_in_bus_ends_at_the_consumer_register(tmp_path):
    r = SC.source_chain(SC.load(geom(tmp_path)), "y_i", False)
    assert abs(r["max_um"] - 600.0) < 0.3 and abs(r["src_centroid"][0] - 700.0) < 0.2


def test_missing_bus_has_no_override_and_leaf_um_is_kept(tmp_path):
    g = SC.load(geom(tmp_path))
    assert SC.source_chain(g, "nope") is None
    t = {"buses": [{"name": "z", "dir": "out"}], "internal_stations": [{"conn": "bus:z", "from_um": [0, 0], "regs_um": [[100, 0]], "to_um": [200, 0]}]}
    assert SC.overrides(g, t) == {} and LB.internal_census(t)["bus:z"]["max_um"] == 100.0


def test_overrides_move_the_chain_end_in_both_checks(tmp_path):
    g = SC.load(geom(tmp_path))
    t = {"outline_um": [1300, 700], "buses": [{"name": "x_o", "dir": "out"}, {"name": "y_i", "dir": "in"}],
         "internal_stations": [{"conn": "bus:x_o", "from_um": [475, 574], "regs_um": [[300, 500]], "to_um": [200, 500], "bits": 2},
                               {"conn": "bus:y_i", "from_um": [50, 50], "regs_um": [[100, 100]], "to_um": [150, 150], "bits": 1}]}
    ov = SC.overrides(g, t)
    assert ov["bus:x_o"]["end"] == "src" and ov["bus:y_i"]["end"] == "dst"
    plan_only = LB.internal_census(t)["bus:x_o"]
    placed = LB.internal_census(t, ov)["bus:x_o"]
    assert plan_only["first_um"] == 249.0 and plan_only["n_over"] == 0
    assert abs(placed["first_um"] - 600.0) < 0.3 and placed["n_over"] >= 1 and placed["moved"]      # worst real edge, not centroid (1080,500) -> (300,500)
    rows = [r for r in RR.type_hops(t, src=ov)[0] if r["conn"] == "bus:x_o"]
    base = [r for r in RR.type_hops(t)[0] if r["conn"] == "bus:x_o"]
    assert abs(rows[0]["man"] - 600.0) < 0.3 and base[0]["man"] == 249.0


def test_spread_sources_do_not_create_a_hop_from_their_mean(tmp_path):
    """sle_su_c x_su_l1_p1_o / x_su_l0_p1_o: four 128-flop source banks 700 um apart feed station 0 from <= 181 um each; the mean of the banks is no register
    and a chain point there read 670.6 / 617.8 um against a real worst edge of 180.8 um.  The override must report the real edge."""
    rows = [("C", 1, "S", "DFF", 100, 100, 100.1, 100.1, "u_bound.u_u_suvm_u_vm8q_u_oc.q\\[0\\]$_DFF_P_"),
            ("C", 2, "S", "DFF", 900, 100, 900.1, 100.1, "u_bound.u_u_suvm_u_vm8q_u_ob.q\\[0\\]$_DFF_P_"),
            ("C", 10, "S", "DFF", 150, 200, 150.1, 200.1, "u_bound.u_ist_x_p_o_0/q0$_DFF_P_"),
            ("C", 11, "S", "DFF", 850, 200, 850.1, 200.1, "u_bound.u_ist_x_p_o_0/q1$_DFF_P_")]
    nets = [("N", "a", "i1", "i10"), ("N", "b", "i2", "i11")]
    p = tmp_path / "g.tsv"
    p.write_text("\n".join("\t".join(str(x) for x in r) for r in rows + nets) + "\n")
    g = SC.load(str(p))
    t = {"outline_um": [1000, 400], "buses": [{"name": "x_p_o", "dir": "out"}],
         "internal_stations": [{"conn": "bus:x_p_o", "from_um": [500, 150], "regs_um": [[500, 200], [600, 200]], "to_um": [700, 200], "bits": 2}]}
    ov = SC.overrides(g, t)
    assert abs(ov["bus:x_p_o"]["xy"][0] - 500.0) < 0.2            # the mean sits between the banks
    c = LB.internal_census(t, ov)["bus:x_p_o"]
    assert abs(c["first_um"] - 150.0) < 0.3 and c["n_over"] == 0   # real worst edge 100 + 50, never the 700 um from the mean
    assert RR.type_hops(t, src=ov)[0][0]["man"] < 151


def test_stale_plan_stage_hops_are_replaced_by_placed_station_edges(tmp_path):
    """sle_su_c x_su_l0_p1_o: plan regs_um hop 474 um, placed station -> station edges <= 304 um: the placed chain wins when geometry exists."""
    rows = [("C", 1, "S", "DFF", 100, 100, 100.1, 100.1, "u_bound.g_src_q$_DFF_P_"),
            ("C", 10, "S", "DFF", 200, 100, 200.1, 100.1, "u_bound.u_ist_x_p_o_0/q0$_DFF_P_"),
            ("C", 11, "S", "DFF", 480, 100, 480.1, 100.1, "u_bound.u_ist_x_p_o_1/q0$_DFF_P_")]
    nets = [("N", "a", "i1", "i10"), ("N", "b", "i10", "i11")]
    p = tmp_path / "g.tsv"
    p.write_text("\n".join("\t".join(str(x) for x in r) for r in rows + nets) + "\n")
    g = SC.load(str(p))
    r = SC.source_chain(g, "x_p_o")
    assert abs(r["inter_max_um"] - 280.0) < 0.3
    t = {"outline_um": [1000, 400], "buses": [{"name": "x_p_o", "dir": "out"}],
         "internal_stations": [{"conn": "bus:x_p_o", "from_um": [50, 100], "regs_um": [[100, 100], [700, 100]], "to_um": [800, 100], "bits": 1}]}
    assert LB.internal_census(t)["bus:x_p_o"]["max_um"] == 600.0                      # plan: stale regs_um hop
    c = LB.internal_census(t, SC.overrides(g, t))["bus:x_p_o"]
    assert abs(c["max_um"] - 280.0) < 0.3 and c["n_over"] == 0                         # placed: 100 / 280 / plan far end 100
