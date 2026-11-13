"""QC-PARAMWRAP 11-12: a count-aligned ring realised by a SIGNED hard child (plan hard_cores[].param_wrap, base
ot_dp_clk_landing_ca/_cas, physical_inst u_bound.u_cland_<bus>) keeps the child's exact parameters in the bound RTL.
The die-wide ring knobs (clock.landing_ring_status_reg / _guard_reg / _fanout_max) re-parameterise soft rings only, so
param_wrap.wrap_bound (the kit-rtl check) accepts the bound ring and the private kit wrapper equals the signed child.
Failing case before the fix: QC s27/s28 cbn_q00__cl622f65d2 / cbn_q00__cldbcda913 kit_rtl "u_cland_na_i00 is
ot_dp_clk_landing_cas #(.W(515), .DEPTH(4), .STATUS_REG(1), ...), plan says ... #(.W(515), .DEPTH(4), .WFALL(1), ...)".
    python3 -m pytest -q tools/die_plan/test_param_wrap_hard_ring.py"""
import re

import pytest

import param_wrap
import clock_landings as CL
from clock_landings import Landings, LandingError
from test_clock_landings import B_BODY
from test_count_straps import strap_vehicle

RING = re.compile(r"^\s+(ot_dp_clk_landing_cas?) (#\([^\n]*?\)) u_cland_y \(", re.M)


def _wreg(p):
    p["partition_types"]["B"].setdefault("clock", {})["landing_ring_wreg"] = dict(buses=["y"], dsrep=1, freg=False)


def _vehicle(**clock):
    p, t = strap_vehicle()
    _wreg(p)
    p.setdefault("clock", {}).update(clock)
    return p, t


def _params(rtl):
    m = RING.search(rtl)
    return m.group(1), {k: int(v) for k, v in re.findall(r"\.(\w+)\((\d+)\)", m.group(2))}


def _hard(p, base, params, master="b_cland_y"):
    hc = dict(inst="cl_y", module=master, physical_master=master, physical_inst="u_bound.u_cland_y",
              param_wrap=dict(base=base, params=dict(params)))
    p["partition_types"]["B"].setdefault("hard_cores", []).append(hc)
    return p["partition_types"]["B"]["hard_cores"]


def _signed_child():
    """the legacy (no die-wide knob) ring parameters = what the child master was generated and signed from"""
    p, t = _vehicle()
    return _params(Landings(p, t).type_rtl("B", B_BODY))


def test_helper():
    hard_ring_params = CL.hard_ring_params
    base, params = _signed_child()
    p, _ = _vehicle()
    assert hard_ring_params(p, "B", "y") is None
    _hard(p, base, params)
    assert hard_ring_params(p, "B", "y") == params and hard_ring_params(p, "B", "x") is None
    assert hard_ring_params(p, "Z", "y", key="B") == params                    # landing base type key


@pytest.mark.parametrize("clock", [dict(landing_ring_status_reg=True), dict(landing_ring_guard_reg=True),
                                   dict(landing_ring_status_reg=True, landing_ring_fanout_max=32)])
def test_die_wide_knobs_keep_the_hard_child(clock):
    base, params = _signed_child()
    # soft ring: the die-wide knob does re-parameterise it (unchanged behaviour)
    p, t = _vehicle(**clock)
    soft = Landings(p, t).type_rtl("B", B_BODY)
    assert ".STATUS_REG(1)" in soft
    # hard ring: the bound ring is the signed child's exact paramod; kit-rtl wrap_bound accepts it
    p, t = _vehicle(**clock)
    hcs = _hard(p, base, params)
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", B_BODY)
    assert _params(rtl) == (base, params)
    assert "STATUS_REG" not in rtl and "GUARD_REG" not in rtl and "RSTREP" not in rtl and "PLACEREP" not in rtl
    assert lg.reset_placements["B"]["y"]["hard_child_params"] == params
    bound, receipt, srcs = param_wrap.wrap_bound(rtl, hcs)
    assert "    b_cland_y u_cland_y (" in bound and receipt[0]["cycles_changed"] == 0
    assert param_wrap.param_text(params) in srcs["b_cland_y"]


def test_child_with_status_reg_keeps_it():
    """a child signed WITH STATUS_REG keeps it even without the die-wide knob"""
    base, params = _signed_child()
    params = {"W": params["W"], "DEPTH": params["DEPTH"], "STATUS_REG": 1,
              **{k: v for k, v in params.items() if k not in ("W", "DEPTH")}}
    p, t = _vehicle()
    hcs = _hard(p, base, params)
    rtl = Landings(p, t).type_rtl("B", B_BODY)
    assert _params(rtl) == (base, params)
    param_wrap.wrap_bound(rtl, hcs)


def test_mismatch_fails_at_bind():
    base, params = _signed_child()
    p, t = _vehicle(landing_ring_status_reg=True)
    _hard(p, base, dict(params, DEPTH=params["DEPTH"] + 4))
    with pytest.raises(LandingError, match="signed hard child"):
        Landings(p, t).type_rtl("B", B_BODY)


def test_explicit_type_opt_in_conflicts():
    base, params = _signed_child()
    p, t = _vehicle()
    p["partition_types"]["B"]["landing_status_reg"] = True
    _hard(p, base, params)
    with pytest.raises(LandingError, match="landing_status_reg"):
        Landings(p, t).type_rtl("B", B_BODY)


def test_child_signed_from_soft_ring_keeps_dsrep():
    """QC-PARAMWRAP-DS 11-13: a child generated from the SOFT ring of the same plan under the die fanout bound (QC s29
    sle_cland_w2104_s_s34: DSREP 8 / RSTREP 34) binds; any other DSREP still fails closed"""
    p, t = _vehicle(landing_ring_status_reg=True, landing_ring_fanout_max=32)
    base, soft = _params(Landings(p, t).type_rtl("B", B_BODY))
    assert soft["DSREP"] > 1
    p, t = _vehicle(landing_ring_status_reg=True, landing_ring_fanout_max=32)
    hcs = _hard(p, base, soft)
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", B_BODY)
    assert _params(rtl) == (base, soft)
    param_wrap.wrap_bound(rtl, hcs)
    p, t = _vehicle(landing_ring_status_reg=True, landing_ring_fanout_max=32)
    _hard(p, base, dict(soft, DSREP=soft["DSREP"] * 2 if soft["DSREP"] < 64 else 1))
    with pytest.raises(LandingError, match="signed hard child"):
        Landings(p, t).type_rtl("B", B_BODY)
