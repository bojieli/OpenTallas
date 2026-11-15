"""STRAP-MASTER-1115: param_wrap rows with straps tie the strap pins and do not match on SKEW*."""
import re

import pytest

import param_wrap as PW

NB0 = "qfd_dv_s8_station_tail1_nb0"


def _row(straps=None, params=None, **kw):
    return dict(inst="u_r0", module="sta_region_strap_s1", physical_master="sta_region_strap_s1", physical_inst="u_bound.u_u_r0",
                param_wrap=dict(base=NB0, params=params if params is not None else {"HI_PAD": 18},
                                straps=straps or {"strap_skew_n": 8, "strap_skew_s": 9}, **kw))


def _bound(params):
    return (f"module t(input ck);\n    {NB0} {params} u_u_r0 (\n        .ck(ck),\n        .rst_n(rst_n));\n"
            f"    other_m #(.X(1)) u_o (.a(a));\nendmodule\n")


def test_ties_inserted_skew_not_matched_master_name_independent_of_skew():
    b1, r1, s1 = PW.wrap_bound(_bound("#(.HI_PAD(18), .SKEW_N(8), .SKEW_S(9))"), [_row()])
    b2, r2, s2 = PW.wrap_bound(_bound("#(.HI_PAD(18), .SKEW_N(9), .SKEW_S(10))"), [_row({"strap_skew_n": 9, "strap_skew_s": 10})])
    assert "sta_region_strap_s1 u_u_r0 (" in b1 and ".strap_skew_n(5'd8), .strap_skew_s(5'd9)," in b1 and ".ck(ck)" in b1
    assert ".strap_skew_n(5'd9), .strap_skew_s(5'd10)," in b2
    assert s1 == s2 and set(s1) == {"sta_region_strap_s1"}                     # the wrapper text carries no strap value
    assert r1[0]["straps"] == {"strap_skew_n": 8, "strap_skew_s": 9} and "SKEW" not in s1["sta_region_strap_s1"].split("u_w")[0].split("module")[1]


def test_instance_without_param_text_and_other_param_mismatch():
    b, r, s = PW.wrap_bound(_bound(""), [_row(params={})])          # module defaults (SKEW 14), no #(...)
    assert "sta_region_strap_s1 u_u_r0 (\n    .strap_skew_n(5'd8)" in b.replace("        ", "    ") or ".strap_skew_n(5'd8)" in b
    with pytest.raises(ValueError, match="plan says"):
        PW.wrap_bound(_bound("#(.HI_PAD(17), .SKEW_N(8))"), [_row()])


def test_wrapper_has_strap_ports_and_base_ports_and_can_be_skipped():
    _, _, s = PW.wrap_bound(_bound("#(.HI_PAD(18))"), [_row()])
    t = s["sta_region_strap_s1"]
    assert "input  wire [4:0] strap_skew_n" in t and "input  wire [4:0] strap_skew_s" in t
    assert "output wire [63:0] r_d" in t and "input  wire [63:0] rs_s_lo_p" in t and f"{NB0} #(.HI_PAD(18)) u_w (" in t
    _, _, s2 = PW.wrap_bound(_bound("#(.HI_PAD(18))"), [_row(wrapper=False)])
    assert s2 == {}


def test_bad_straps_fail_closed():
    with pytest.raises(ValueError, match="does not fit 5 bits"):
        PW.wrap_bound(_bound("#(.HI_PAD(18))"), [_row({"strap_skew_n": 32, "strap_skew_s": 9})])
    with pytest.raises(ValueError, match="straps"):
        PW.wrap_bound(_bound("#(.HI_PAD(18))"), [_row({"strap_skew_n": 8})])


def test_rows_without_straps_behave_as_before():
    row = dict(inst="u_r0", module="m_w", physical_master="m_w", physical_inst="u_bound.u_u_r0",
               param_wrap=dict(base=NB0, params={"SKEW_N": 8}))
    b, r, s = PW.wrap_bound(_bound("#(.SKEW_N(8))"), [row])
    assert "m_w u_u_r0 (" in b and "strap" not in b and "strap" not in s["m_w"]
    with pytest.raises(ValueError, match="plan says"):
        PW.wrap_bound(_bound("#(.SKEW_N(9))"), [row])


# ---- s2 master: HI_PAD strapped too (strap_hi_pad[4:0]) ----
S2 = {"strap_skew_n": 9, "strap_skew_s": 11, "strap_hi_pad": 18}


def test_hi_pad_strap_ties_and_is_not_matched():
    b, r, s = PW.wrap_bound(_bound("#(.HI_PAD(18), .SKEW_N(9), .SKEW_S(11))"), [_row(S2, params={})])
    assert ".strap_skew_n(5'd9), .strap_skew_s(5'd11), .strap_hi_pad(5'd18)," in b
    t = s["sta_region_strap_s2"] if "sta_region_strap_s2" in s else s["sta_region_strap_s1"]
    assert "strap_hi_pad" in t and t.count("input  wire [4:0] strap_") == 3
    # a row that still lists HI_PAD in params: it is a strap now, so the plan value is not matched in the text
    PW.wrap_bound(_bound("#(.HI_PAD(18), .SKEW_N(9), .SKEW_S(11))"), [_row(S2, params={"HI_PAD": 5})])
    # the skew-only row (s1 form) still compares HI_PAD in the text
    with pytest.raises(ValueError, match="plan says"):
        PW.wrap_bound(_bound("#(.HI_PAD(17), .SKEW_N(8), .SKEW_S(9))"), [_row()])


def test_hi_pad_strap_range_and_required_pair():
    with pytest.raises(ValueError, match="does not fit 5 bits"):
        PW.wrap_bound(_bound("#()"), [_row(dict(S2, strap_hi_pad=32), params={})])
    with pytest.raises(ValueError, match="must include"):
        PW.wrap_bound(_bound("#()"), [_row({"strap_hi_pad": 3}, params={})])
    assert PW.bound_strap_value(NB0, {}, "strap_hi_pad") == 0          # HI_PAD default 0
    assert PW.bound_strap_value(NB0, {"SKEW": "12"}, "strap_skew_n") == 12
    assert PW.bound_strap_value(NB0, {"SKEW": "12", "HI_PAD": "7"}, "strap_hi_pad") == 7
