"""S81-RINGHOLD-4 variant (a): plan clock.ring_hold.write_edge "fall" makes the plain landing rings write on the falling
fclk edge and moves their input max to the T/2 budget; lint keeps the lowered budget as the floor.  Absent = unchanged."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock_landings as CL  # noqa: E402
import gen_phys  # noqa: E402
import landing_contract as LC  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402
from test_ring_input_sdc import _ring_kit  # noqa: E402
from test_sdc_lint import _errs  # noqa: E402


def _plan(P, edge):
    raw = copy.deepcopy(P.raw)
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["ring_hold"] = dict(sender_ps=80, **({"write_edge": edge} if edge else {}))
    return schema.Plan(raw)


def _max(s, ck):
    tail = s.split(LC.RING_INPUTS_TAG, 1)[1]
    return next(float(ln.split()[2]) for ln in tail.splitlines() if ln.startswith(f"set_input_delay -max") and ck in ln)


def test_fall_moves_ring_max_by_half_period_and_lints():
    P0, tn, b, _w = _ring_kit()
    ck = f"fclk_in_{b}"
    Pr, Pf = _plan(P0, None), _plan(P0, "fall")
    pins = gen_phys.type_pins(Pf, tn)
    sr, sf = gen_phys.sdc(Pr, tn, pins), gen_phys.sdc(Pf, tn, pins)
    per = gen_phys.t_lib(P0.die["period_ps"])
    assert LC.ring_fall_clocks(Pr, tn) == set() and LC.ring_fall_clocks(Pf, tn) == {ck}
    assert abs(_max(sr, ck) - per / 2 - _max(sf, ck)) < 1e-3
    ctx = sdc_lint.kit_context(Pf, tn)
    assert _errs(sf, ctx) == []
    # a lower budget still is a relaxation
    bad = sf.replace(f"set_input_delay -max {_max(sf, ck):.4f} -clock {ck}", f"set_input_delay -max {_max(sf, ck) - 50:.4f} -clock {ck}")
    assert any("relaxation" in e for e in _errs(bad, ctx))


def test_rise_is_the_same_text_as_absent():
    P0, tn, _b, _w = _ring_kit()
    a, b = _plan(P0, None), _plan(P0, "rise")
    pins = gen_phys.type_pins(a, tn)
    assert gen_phys.sdc(a, tn, pins) == gen_phys.sdc(b, tn, pins)


def test_ring_write_fall_flag():
    assert CL.ring_write_fall({"clock": {"ring_hold": {"sender_ps": 1, "write_edge": "fall"}}})
    assert not CL.ring_write_fall({"clock": {"ring_hold": {"sender_ps": 1}}})
    assert not CL.ring_write_fall({"clock": {}}) and not CL.ring_write_fall({})


def test_plain_ring_gets_wneg_only_with_fall():
    from test_clock_landings import vehicle
    b = ("module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
         " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n")
    p, t = vehicle()
    assert "ot_dp_clk_landing #(.W(5)) u_cland_y (" in CL.Landings(p, t).type_rtl("B", b)
    p, t = vehicle()
    p["clock"] = {"ring_hold": {"sender_ps": 80, "write_edge": "fall"}}
    assert "ot_dp_clk_landing #(.W(5), .WNEG(1)) u_cland_y (" in CL.Landings(p, t).type_rtl("B", b)
    p, t = vehicle()      # a count-aligned / other ring module never gets WNEG
    p["clock"] = {"ring_hold": {"sender_ps": 80, "write_edge": "fall"}}
    t["ports"][0].update(ring_module="ot_dp_clk_landing_ca", ring_params=dict(DEPTH=4, K=3), ring_ports=dict(t_rst_n="rr_parent"))
    assert "WNEG" not in CL.Landings(p, t).type_rtl("B", b)


# HEAD-RINGHOLD-1 (COORD 10-31 14:4x (3), option A): the count-aligned rings take the same falling-edge write (WFALL)
def _fall(types=None):
    return {"ring_hold": dict(sender_ps=80, write_edge="fall", **({"write_fall_types": types} if types else {}))}


def test_ring_write_fall_type_scope():
    p = {"clock": _fall(["hd_turn_a"])}
    assert CL.ring_write_fall(p) and CL.ring_write_fall(p, "hd_turn_a") and CL.ring_write_fall(p, "hd_turn_a__x1")
    assert not CL.ring_write_fall(p, "hd_turn_b") and CL.ring_write_fall({"clock": _fall()}, "any")


def test_count_aligned_ring_gets_wfall_only_with_fall():
    from test_clock_landings import B_BODY, ca_vehicle
    from test_count_straps import strap_vehicle
    p, t = ca_vehicle()
    base = CL.Landings(p, t).type_rtl("B", B_BODY)
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-2)) u_cland_y" in base and "WFALL" not in base
    for clock, want in ((_fall(), True), (_fall(["B"]), True), (_fall(["A"]), False),
                        ({"ring_hold": {"sender_ps": 80, "write_edge": "rise"}}, False)):
        p, t = ca_vehicle()
        p["clock"] = clock
        bb = CL.Landings(p, t).type_rtl("B", B_BODY)
        assert ("ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-2), .WFALL(1)) u_cland_y" in bb) == want
        assert bb == base or want                      # not selected: byte-identical text
        assert bb.replace(", .WFALL(1)", "") == base   # the parameter is the only difference
    p, t = strap_vehicle()
    p["clock"] = _fall()
    bb = CL.Landings(p, t).type_rtl("B", B_BODY)
    assert "ot_dp_clk_landing_cas #(.W(5), .DEPTH(4), .WFALL(1)) u_cland_y" in bb


def test_per_row_count_aligned_ring_gets_wfall():
    from test_clock_landings import vehicle
    b = ("module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
         " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n")
    p, t = vehicle()
    p["clock"] = _fall()
    t["ports"][0].update(ring_module="ot_dp_clk_landing_ca", ring_params=dict(DEPTH=4, K=3), ring_ports=dict(t_rst_n="rr_parent"))
    bb = CL.Landings(p, t).type_rtl("B", b)
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(3), .WFALL(1)) u_cland_y (" in bb and "WNEG" not in bb


def test_verify_moves_the_lag_window_by_half_period_for_fall_writers():
    import count_align_bind as CB
    from test_count_align_bind import row, run, T
    _p, b, v = run([row("P", "r0", "r1", 100.0)])
    vf = CB.verify(b, 400, fall_ports={"P"})
    # the fall write is T/2 earlier: low guard margin +T/2, high guard margin -T/2
    assert abs((vf["sim_min_margin_low_ps"] - v["sim_min_margin_low_ps"]) - T / 2) < 0.2
    assert abs((v["sim_min_margin_high_ps"] - vf["sim_min_margin_high_ps"]) - T / 2) < 0.2
    assert vf["write_fall_ports"] == 1 and "write_fall_ports" not in v
    die = {"clock": _fall(["B"]), "partitions": [{"name": "r1", "type": "B"}, {"name": "r0", "type": "A"}],
           "ports": [{"id": "P", "src": {"part": "r0"}, "dst": {"part": "r1"}}]}
    assert CB.write_fall_ports(b, die) == {"P"}
    die["clock"] = _fall(["A"])
    assert CB.write_fall_ports(b, die) == set()
    assert CB.write_fall_ports(b, {"partitions": [], "ports": []}) == set()
