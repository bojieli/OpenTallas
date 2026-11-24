import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sta_ep_census as C  # noqa: E402

SUM = """Startpoint                                    Endpoint                                      Slack
--------------------------------------------------------------------------------
u_bound.u_lpad_chd_q_1/r_reg_518_/CLK (DFFHQNx1) u_bound.u_ctl.q_reg_3_/D (DFFHQNx1) -276.21
u_bound.u_lpad_chd_q_1/r_reg_519_/CLK (DFFHQNx1) u_bound.u_ctl.q_reg_4_/D (DFFHQNx1) -30.00
in_x[3] (in) u_bound.rrl_833.q/D (DFFHQNx1) -50.50
u_bound.u_u_rp.g_wgrp_2.r/CLK (DFF) out_y[0] (out) 12.00
"""


def test_cls():
    assert C.cls("in_x[3]") == "PORT:in_x"
    assert C.cls("u_bound.rrl_833.q") == "rrl"
    assert C.cls("u_bound.u_pd7.q") == "u_pd#"
    assert C.cls("u_bound.u_u_rp.g_wgrp_2.r") == "u_u_rp.g_wgrp"
    assert C.cls("u_bound.u_ctl.q_reg_3_") == "u_ctl"


def test_census_groups_and_threshold():
    rows = C.parse(SUM.splitlines())
    assert len(rows) == 4
    out = C.census(rows, -42.0)
    assert out[0] == "endpoints listed 4 violating 3 below -42.0: 2"
    body = out[2:]
    assert len(body) == 2
    assert body[0].split()[:3] == ["2", "1", "-276.21"]
    assert body[0].endswith("u_lpad_chd_q -> u_ctl")
    assert body[1].split()[:3] == ["1", "1", "-50.50"] and body[1].endswith("PORT:in_x -> rrl")
