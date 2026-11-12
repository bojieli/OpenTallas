"""stage_s81_tapwin_floor: phy per_type 0 is raised so the HEAD-95 floor acts (GEN-CLASS-1 11-12)."""
import stage_s81_tapwin_floor as S


def _plan():
    return {"clock": {"tap_window": {"window_ps": 180.0,
                                     "per_type_ps": {"phy__t1": 0.0, "st_a": 100.0},
                                     "per_port_ps": {"st_a": {"clk": 0.0, "clk_t1": 25.0}}}}}


KW = {"per_port_ps": {"phy__t1": {"clk": 0.0}, "st_a": {"clk": 2.0}}}


def test_phy_raised_and_floored():
    P = _plan()
    pre, ch = S.stage(P, KW)
    tw = P["clock"]["tap_window"]
    assert tw["per_type_ps"]["phy__t1"] == 20.0
    assert tw["per_port_ps"]["phy__t1"] == {"clk": 10.0}
    assert tw["per_port_ps"]["st_a"] == {"clk": 10.0, "clk_t1": 25.0}      # floor only by default
    assert {c[0] for c in ch} == {"phy__t1", "st_a"}


def test_without_stage_floor_cannot_act_on_phy():
    import tap_window_floor as TWF
    P = _plan()
    TWF.floor_windows(P, KW)
    assert "phy__t1" not in P["clock"]["tap_window"]["per_port_ps"]


def test_floor_needs_opt_in():
    P = _plan()
    S.stage(P, KW, floor_needs=True)
    assert P["clock"]["tap_window"]["per_port_ps"]["st_a"]["clk"] == 12.0


def test_idempotent():
    P = _plan()
    S.stage(P, KW)
    pre, ch = S.stage(P, KW)
    assert pre == [] and ch == []


if __name__ == "__main__":
    test_phy_raised_and_floored(); test_without_stage_floor_cannot_act_on_phy(); test_floor_needs_opt_in(); test_idempotent()
    print("OK 4")
