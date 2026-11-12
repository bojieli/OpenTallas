"""KW-FIX-45 11-12: param_wrap's expected landing-ring parameters come from the same clock_landings predicates that write the RTL."""
import pytest
import param_wrap as PW

BASE = "ot_dp_clk_landing_cas"
PARAMS = {"W": 515, "DEPTH": 4, "WFALL": 1, "WREG": 1, "DSREP": 1}


def bound(text_params):
    return f"module m;\n    {BASE} #({text_params}) u_cland_na_i00 (.d(d));\nendmodule\n"


def core():
    return [{"inst": "cl_na_i00", "module": "wrapped_cl", "physical_inst": "u_bound.u_cland_na_i00",
             "param_wrap": {"base": BASE, "params": dict(PARAMS)}}]


def test_flag_off_literal_matches_unchanged():
    b = bound(".W(515), .DEPTH(4), .WFALL(1), .WREG(1), .DSREP(1)")
    out, rec, srcs = PW.wrap_bound(b, core(), {})
    assert "wrapped_cl u_cland_na_i00 (" in out and rec[0]["params"] == PARAMS


def test_die_wide_status_reg_is_expected_in_rtl_order():
    b = bound(".W(515), .DEPTH(4), .STATUS_REG(1), .WFALL(1), .WREG(1), .DSREP(1)")
    out, rec, srcs = PW.wrap_bound(b, core(), {"landing_ring_status_reg": True})
    assert list(rec[0]["params"]) == ["W", "DEPTH", "STATUS_REG", "WFALL", "WREG", "DSREP"]
    assert ".STATUS_REG(1)" in srcs["wrapped_cl"]                       # the generated wrapper carries it too
    with pytest.raises(ValueError, match="plan says"):                  # flag off: the STATUS_REG RTL is a real mismatch
        PW.wrap_bound(b, core(), {})


def test_guard_reg_implies_status_reg():
    b = bound(".W(515), .DEPTH(4), .STATUS_REG(1), .GUARD_REG(1), .WFALL(1), .WREG(1), .DSREP(1)")
    out, rec, _ = PW.wrap_bound(b, core(), {"landing_ring_guard_reg": True})
    assert list(rec[0]["params"]) == ["W", "DEPTH", "STATUS_REG", "GUARD_REG", "WFALL", "WREG", "DSREP"]


def test_real_mismatch_is_still_rejected_with_the_flag_on():
    b = bound(".W(516), .DEPTH(4), .STATUS_REG(1), .WFALL(1), .WREG(1), .DSREP(1)")
    with pytest.raises(ValueError, match="plan says"):
        PW.wrap_bound(b, core(), {"landing_ring_status_reg": True})


def test_declared_status_reg_is_not_duplicated_and_other_bases_unchanged():
    assert PW.landing_ring_params(BASE, {"W": 8, "DEPTH": 4, "STATUS_REG": 1}, {"landing_ring_status_reg": True}) == {"W": 8, "DEPTH": 4, "STATUS_REG": 1}
    assert PW.landing_ring_params("some_other_base", dict(PARAMS), {"landing_ring_status_reg": True}) == PARAMS
