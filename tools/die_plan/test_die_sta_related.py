"""die_sta_related.py kit-contract hold bound (INFRA-FIRST-R3b): bound = declared window - hold damage, CPPR at the
last common tree node; zero-logic numbers unchanged."""
import die_sta_related as R

REG = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=46.5, setup_ps=5.6, hold_ps=22.2)


def _taps():
    # region root "h0" range 10 ps; a/b in one partition, c in a neighbour; all in region h0
    return {"a": dict(late_ps=1000.0, early_ps=990.0, cppr_node="h0"),
            "b": dict(late_ps=1050.0, early_ps=1040.0, cppr_node="h0"),
            "c": dict(late_ps=1020.0, early_ps=1010.0, cppr_node="h0")}


def test_contract_bound_intra_and_seam():
    taps, rng = _taps(), {"h0": 10.0, "h": 30.0}
    pairs = [("a", "b", "p"), ("b", "a", "p")]
    r = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, hold_window=dict(ps=0.0, basis="t"))
    kc = r["kit_contract_hold"]
    # a -> b: damage = b.late - a.early - credit(10) = 1050 - 990 - 10 = 50
    assert kc["window_needed_ps"] == 50.0 and kc["worst_hold_bound_ps"] == -50.0 and kc["verdict"] == "FAIL"
    assert kc["neg_pairs"] == 1
    # zero-logic hold unchanged: 990 + 46.5 - (1050 + 22.2) - 25 + 10
    assert r["worst_hold_slack_ps"] == round(990 + 46.5 - 1050 - 22.2 - 25 + 10, 2)
    r2 = R.time_class([("a", "c", "p->q")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0,
                      hold_window=dict(ps=40.0, basis="legacy"))
    assert r2["kit_contract_hold"]["worst_hold_bound_ps"] == 20.0 and r2["kit_contract_hold"]["verdict"] == "PASS"


def test_no_window_no_contract_block():
    r = R.time_class([("a", "b", "p")], _taps(), {"h0": 10.0}, REG, 20.0, 833.333, 60.0, 25.0)
    assert "kit_contract_hold" not in r


def test_windows_read_from_plan():
    legacy = R.kit_windows(dict(insertion_tol_ps=40))
    assert legacy["intra"]["ps"] == 0.0 and legacy["seam"]["ps"] == 40.0
    w = R.kit_windows(dict(insertion_tol_ps=40, seam_hold=dict(sender_ps=25, seam_ps=80), tap_window=dict(window_ps=80)))
    assert w["intra"]["ps"] == 80.0 and w["seam"]["ps"] == 80.0 and "clock.tap_window" in w["intra"]["basis"]
    wi = R.kit_windows(dict(tap_window=dict(window_ps=80)), 120.0)
    assert wi["intra"]["ps"] == 120.0 and "WHAT-IF" in wi["intra"]["basis"]


# ---- REAL VIEWS (CLOCK-KV-R16, opt-in)
ETM = """library (t) {
  cell ("c") {
    bus("ck") {
    pin("ck[0]") {
      direction : input;
      clock : true;
      timing() {
        timing_type : min_clock_tree_path;
        cell_rise(scalar) {
          values("260.0");
        }
      }
      timing() {
        timing_type : max_clock_tree_path;
        cell_rise(scalar) {
          values("300.0");
        }
      }
    }
    }
    pin("d[0]") {
      direction : input;
      timing() {
        related_pin : "ck[0]";
        timing_type : hold_rising;
        rise_constraint(scalar) {
          values("120.0");
        }
        fall_constraint(scalar) {
          values("125.0");
        }
      }
      timing() {
        related_pin : "ck[0]";
        timing_type : setup_rising;
        rise_constraint(scalar) {
          values("-90.0");
        }
      }
    }
    pin("q[0]") {
      direction : output;
      timing() {
        related_pin : "ck[0]";
        timing_type : rising_edge;
        cell_rise(template_1) {
          index_1("2.0, 10.0");
          values("370.0,390.0");
        }
        cell_fall(template_1) {
          index_1("2.0, 10.0");
          values("360.0,380.0");
        }
      }
    }
  }
}
"""


def test_parse_etm(tmp_path):
    f = tmp_path / "c_tt.lib"
    f.write_text(ETM)
    e = R.parse_etm(f, 6.0)
    assert e["clock_pin"] == "ck[0]" and e["clock_tree_path_ps"] == {"min_clock_tree_path": 260.0,
                                                                     "max_clock_tree_path": 300.0}
    assert e["out_max_ps"] == 380.0 and e["out_min_ps"] == 370.0      # interpolated at 6 fF
    assert e["in_setup_ps"] == -90.0 and e["in_hold_ps"] == 125.0


def test_budget_views_reproduce_declared_formula():
    taps, rng = _taps(), {"h0": 10.0}
    pairs = [("a", "b", "p"), ("b", "a", "p")]
    base = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0)
    v = {p: [R.budget_model(REG, 250.0)] for p in taps}
    r = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, views=v)
    assert r["worst_setup_slack_ps"] == base["worst_setup_slack_ps"]
    assert r["worst_hold_slack_ps"] == base["worst_hold_slack_ps"]
    assert r["real_view"]["pairs_with_real_endpoint"] == 0


def test_core_view_pair_uses_etm_arcs():
    taps, rng = _taps(), {"h0": 10.0}
    core = dict(name="core:c", real=True, lat_late=0.0, lat_early=0.0, clkq_max=380.0, clkq_min=370.0, setup=-90.0,
                hold=125.0)
    v = {"a": [R.budget_model(REG, 250.0)], "b": [R.budget_model(REG, 250.0), core]}
    r = R.time_class([("a", "b", "p")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0, views=v)
    rv = r["real_view"]
    assert rv["pairs_with_real_endpoint"] == 1 and rv["pairs_both_real"] == 0
    # budget a -> core b hold: (990 + 250 + 46.5) - (1050 + 0 + 125) - 25 + credit 10
    assert rv["worst_hold_slack_ps"] == round(990 + 250 + 46.5 - 1050 - 125 - 25 + 10, 2)
    # setup: (1040 + 0 + 833.333 + 90) - (1000 + 250 + 68) - 60 + 10
    assert rv["worst_setup_slack_ps"] == round(1040 + 833.333 + 90 - 1000 - 250 - 68 - 60 + 10, 2)
    assert rv["worst_hold"]["capture_model"] == "core:c"
    assert r["worst_hold_slack_ps"] <= rv["worst_hold_slack_ps"]
