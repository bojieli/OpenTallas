"""KW-FIX-5 safe form A: a planned early core tap pin is read against the bound view."""
import gen_phys as G
import schema as S
from test_corelat import pair_with_core

LIB = """library(x) { time_unit : "1ps";
 cell(m) {
  pin(clk) { clock : true; direction : input;
   timing() { timing_type : max_clock_tree_path; cell_rise(s) { values("VIEW"); } cell_fall(s) { values("VIEW"); } }
  }
 }
}
"""


def plan(tmp_path, view_ps, tap_name="u_c.ck", tt=419.0):
    raw = pair_with_core(tt, None)
    raw["partition_types"]["fa"]["clock"]["taps"][0]["name"] = tap_name
    lib = tmp_path / "m.lib"
    lib.write_text(LIB.replace("VIEW", str(view_ps)))
    raw["partition_types"]["fa"]["hard_cores"] = [{"inst": "u_c", "module": "m", "lib": str(lib)}]
    return S.Plan(raw)


def _view_ok(tmp_path, P):
    import cores as C
    ck = C.clock_pins(P.types["fa"]["hard_cores"][0])
    assert "clk" in ck and ck["clk"]["rise"] > 0, "fixture lib must parse: %r" % ck
    return ck


def test_absent_pin_takes_view_pin_and_clamped_early(tmp_path):
    P = plan(tmp_path, 690.0)
    _view_ok(tmp_path, P)
    assert G.core_tap_rows(P, "fa")[0] == ("clk_c0", "u_c", "clk", 250.0, 690.0)
    n, i, p, early, ins = G.core_tap_rows(P, "fa", "FF")[0]
    assert (n, i, p) == ("clk_c0", "u_c", "clk")
    assert ins == round(0.81 * 690.0, 3) and early == S.common_latency_ps(P, "FF")
    r = G.core_tap_view_report(P, "fa")[0]
    assert r["plan_pin"] == "ck" and r["view_pin"] == "clk" and r["clamped"]


def test_early_below_clamp_is_view_minus_common(tmp_path):
    P = plan(tmp_path, 400.0)
    _view_ok(tmp_path, P)
    assert G.core_tap_rows(P, "fa")[0][3:] == (150.0, 400.0)
    assert not G.core_tap_view_report(P, "fa")[0]["clamped"]


def test_pin_on_view_keeps_plan_values(tmp_path):
    P = plan(tmp_path, 690.0, "u_c.clk")
    _view_ok(tmp_path, P)
    assert G.core_tap_rows(P, "fa")[0] == ("clk_c0", "u_c", "clk", 169.0, 419.0)
    assert G.core_tap_view_report(P, "fa") == []


def test_no_view_keeps_plan_pin(tmp_path):
    raw = pair_with_core(419.0, None)
    raw["partition_types"]["fa"]["clock"]["taps"][0]["name"] = "u_c.ck"
    raw["partition_types"]["fa"]["hard_cores"] = [{"inst": "u_c"}]
    assert G.core_tap_rows(S.Plan(raw), "fa")[0][1:] == ("u_c", "ck", 169.0, 419.0)
