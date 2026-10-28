"""QK-CORES-9: gen_core_kit_kv binds the kit clock (SDC / face_flops skip / boundary roles) to the port the shipped core top
RTL feeds to its members, not to a stale core-json class (kv3_pv_pair R8/R9: core json s0__clk 'clk', RTL s1__clk ->
29724 FF without a clock arrival)."""
import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("gk", Path(__file__).with_name("gen_core_kit_kv.py"))
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)

TOP = """// s0__clk mentioned in a comment only
module kv3_pv_pair (
    input wire [0:0] s0__clk,
    input wire [0:0] s0__rst_n,
    input wire [0:0] s1__clk,
    input wire [7:0] s0__d,
    output wire [7:0] s0__q
);
    /* s0__clk */
    leaf u_s0 (.clk(%s[0]), .rst_n(s0__rst_n[0]), .d(s0__d), .q(s0__q));
    leaf u_s1 (.clk(%s[0]), .rst_n(s0__rst_n[0]), .d(s0__d), .q());
endmodule
"""


def cj0():
    return dict(module="kv3_pv_pair",
                pin_class={"s0__clk[0]": "clk", "s1__clk[0]": "clk_unused", "s0__rst_n[0]": "in", "s0__d[0]": "in"},
                report=dict(clock_nets={"clk": "s0__clk[0]"}, clk_unused=["s1__clk[0]"]),
                boundary_role={"s0__clk": "clk", "s1__clk": "clk_unused", "s0__rst_n": "reset"})


def test_consistent_binding_unchanged():
    cj = cj0(); ref = copy.deepcopy(cj)
    assert gk.rtl_clock_binding(TOP % ("s0__clk", "s0__clk"), "kv3_pv_pair", cj) is None
    assert cj == ref


def test_pv_pair_r9_stale_binding_rebound_to_rtl():
    cj = cj0()
    note = gk.rtl_clock_binding(TOP % ("s1__clk", "s1__clk"), "kv3_pv_pair", cj)
    assert note["core_json_clk"] == ["s0__clk"] and note["rtl_clk"] == ["s1__clk"]
    assert cj["pin_class"]["s1__clk[0]"] == "clk" and cj["pin_class"]["s0__clk[0]"] == "clk_unused"
    assert cj["report"]["clock_nets"] == {"clk": "s1__clk[0]"} and cj["report"]["clk_unused"] == ["s0__clk[0]"]
    assert cj["boundary_role"]["s1__clk"] == "clk" and cj["boundary_role"]["s0__clk"] == "clk_unused"
    clks, rsts = gk.core_clocks_resets(cj)
    assert clks == ["s1__clk"]          # -> create_clock [get_ports {s1__clk}] and face_flops ff_skip_re


def test_two_roots_fail_closed():
    with pytest.raises(SystemExit, match="two clock roots"):
        gk.rtl_clock_binding(TOP % ("s0__clk", "s1__clk"), "kv3_pv_pair", cj0())


def test_no_clock_used_fail_closed():
    with pytest.raises(SystemExit, match="no clock-class port"):
        gk.rtl_clock_binding(TOP % ("s0__d", "s0__d"), "kv3_pv_pair", cj0())


def test_multi_clock_core_unchanged():
    cj = dict(module="m", pin_class={"ck[0]": "clk", "ck_hbm[0]": "clk"}, report=dict(clock_nets={"clk": "ck[0]"}))
    top = "module m (input wire [0:0] ck, input wire [0:0] ck_hbm);\n a u (.c(ck[0]), .h(ck_hbm[0]));\nendmodule\n"
    assert gk.rtl_clock_binding(top, "m", cj) is None


def test_prefix_names_do_not_count_as_use():
    # 's0__clk_x' / 'xs0__clk' must not count as a use of s0__clk
    cj = cj0()
    top = (TOP % ("s1__clk", "s1__clk")).replace("leaf u_s1", "wire s0__clk_x; wire xs0__clk; leaf u_s1")
    note = gk.rtl_clock_binding(top, "kv3_pv_pair", cj)
    assert note["rtl_clk"] == ["s1__clk"]
