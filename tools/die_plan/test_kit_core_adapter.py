"""kit_core_clocks.adapt_core_ports: merge and tie a core's port form in the kit copy, fail closed."""
import pytest
import kit_core_clocks as K

BOUND = """    kv3_x u_c (
        .a__ck(clk),
        .a__rst_n(r),
        .d(q),
        .b__ck(clk),
        .b__rst_n(r)
    );
"""
SPEC = {"merge": {"ck": ["a__ck", "b__ck"], "a__rst_n": ["a__rst_n", "b__rst_n"]}, "tie": {"rst_n": "1'b1"}}


def test_merge_and_tie():
    out, rec = K.adapt_core_ports(BOUND, [dict(inst="c", module="kv3_x", native_port_adapter=SPEC)])
    assert ".ck(clk)" in out and ".a__rst_n(r)" in out and ".rst_n(1'b1)" in out and ".d(q)" in out
    assert "b__ck" not in out and "a__ck" not in out and "b__rst_n" not in out
    assert rec[0]["cycles_changed"] == 0 and out.rstrip().endswith(");")


def test_no_spec_unchanged():
    assert K.adapt_core_ports(BOUND, [dict(inst="c", module="kv3_x")]) == (BOUND, [])


def test_two_nets_refused():
    with pytest.raises(ValueError, match="not one net"):
        K.adapt_core_ports(BOUND.replace(".b__ck(clk)", ".b__ck(clk2)"),
                           [dict(inst="c", module="kv3_x", native_port_adapter=SPEC)])


def test_missing_pin_refused():
    with pytest.raises(ValueError, match="found 0"):
        K.adapt_core_ports(BOUND.replace(".b__ck(clk),\n", ""),
                           [dict(inst="c", module="kv3_x", native_port_adapter=SPEC)])
