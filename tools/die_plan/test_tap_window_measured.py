"""KW-FIX-4-SDC (COORD RULING 2026-11-03 10:49, plain-seam input-face class): measured per-port kit tap window
(plan clock.tap_window.per_port_ps from die_sta_related --kit-window-out) instead of the flat -W on every tap port,
CPPR credit for same-root taps in the measured need, fallback to the flat W when the data is missing."""
import json
from pathlib import Path

import pytest

import die_sta_related as DSR
import gen_phys
import schema
import sdc_lint
import signoff

HERE = Path(__file__).parent
PORTS = ["clk", "clk_t1", "clk_t2", "clk_t3", "clk_t4", "clk_t5", "clk_t6", "clk_t7", "clk_t8"]


def _raw(per_port=None, window=80.0):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["tap_window"] = dict(window_ps=window, related_pair_ps=window, note="flat W")
    if per_port is not None:
        raw["clock"]["tap_window"]["per_port_ps"] = per_port
    return raw


def _sdc(P, tn="src"):
    return gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))


MEAS = {"src": {"clk": 0, "clk_t1": 12, "clk_t2": 12, "clk_t3": 30, "clk_t4": 30, "clk_t5": 30, "clk_t6": 45,
                "clk_t7": 45, "clk_t8": 61}}


def test_schema_accepts_per_port():
    assert schema.validate(_raw(MEAS)) == []
    assert schema.validate(_raw({"src": {"clk": -1}}))


def test_window_from_data_per_port_lines_and_io_shift():
    P = schema.Plan(_raw(MEAS))
    s = _sdc(P)
    assert "set_clock_latency -source -early -clock clk 0.0000 [get_ports {clk}]" in s
    assert "set_clock_latency -source -early -clock clk -12.0000 [get_ports {clk_t1 clk_t2}]" in s
    assert "set_clock_latency -source -early -clock clk -30.0000 [get_ports {clk_t3 clk_t4 clk_t5}]" in s
    assert "set_clock_latency -source -early -clock clk -61.0000 [get_ports {clk_t8}]" in s
    assert f"set_clock_latency -source -late -clock clk 0.0000 [get_ports {{{' '.join(PORTS)}}}]" in s
    assert "-80.0000" not in s                      # the flat W is gone on a fully measured type
    assert "MEASURED per port" in s and "FALLBACK" not in s
    # IO: input max shifted by the largest window (61), output min by the smallest (0) -> sender hold never looser
    assert gen_phys.tap_window_io_shift(P, "src") == (-61.0, 0.0)
    assert "set_input_delay -max 105.6000 -clock vclk $non_clk_in" in s      # 166.6 - 61
    assert f"set_output_delay -min {gen_phys.hold_out_min_ps(P):.4f} -clock vclk [all_outputs]" in s
    assert gen_phys.tap_window_max_ps(P, "src") == 61.0 and gen_phys.tap_window_min_ps(P, "src") == 0.0


def test_lint_kit_context_and_tamper():
    P = schema.Plan(_raw(MEAS))
    s, ctx = _sdc(P), sdc_lint.kit_context(P, "src")
    assert ctx["tap_window_port_ps"]["clk_t8"] == 61.0 and ctx["tap_window_in_ps"] == 61.0
    assert ctx["tap_window_ps"] == 0.0                # output-min shift (sign-off overlay hout)
    assert sdc_lint.lint(s, **ctx) == []
    assert sdc_lint.lint(s.replace("-early -clock clk -61.0000", "-early -clock clk -40.0000"), **ctx)
    assert sdc_lint.lint(s.replace("set_input_delay -max 105.6000", "set_input_delay -max 100.0000"), **ctx)
    t = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind", hold_in_min=ctx["hold_in_min_ps"],
                            hold_out_min=ctx["hold_out_min_ps"], tap_window=ctx["tap_window_ps"])
    assert "set_output_delay -min -25 " in t


def test_kit_config_hold_gate_window_is_the_largest(tmp_path):
    P = schema.Plan(_raw(MEAS))
    kit = gen_phys.write_type_kit(P, "src", tmp_path, [])
    assert "export OT_TAP_WINDOW = 61.0000" in (kit / "config.mk").read_text()
    lctx = json.loads((kit / "sdc_lint.json").read_text())
    assert sdc_lint.lint((kit / "constraint.sdc").read_text(), **lctx) == []


def test_fallback_no_data_is_byte_identical(capsys):
    flat = schema.Plan(_raw())
    meas = schema.Plan(_raw(MEAS))
    # 'mid' has no entry: its SDC is byte-identical to the plan without any per-port data, flat -80
    assert _sdc(meas, "mid") == _sdc(flat, "mid")
    assert "-early -clock clk -80.0000" in _sdc(meas, "mid")
    assert sdc_lint.kit_context(meas, "mid") == sdc_lint.kit_context(flat, "mid")
    assert "TAP_WINDOW FALLBACK" in capsys.readouterr().err


def test_fallback_per_missing_port():
    part = {"src": {k: v for k, v in MEAS["src"].items() if k != "clk_t8"}}
    P = schema.Plan(_raw(part))
    s = _sdc(P)
    assert gen_phys.tap_window_fallback_ports(P, "src") == ["clk_t8"]
    assert "set_clock_latency -source -early -clock clk -80.0000 [get_ports {clk_t8}]" in s
    assert "FALLBACK W 80 ps on unmeasured ports clk_t8" in s
    assert gen_phys.tap_window_io_shift(P, "src") == (-80.0, 0.0)
    assert sdc_lint.lint(s, **sdc_lint.kit_context(P, "src")) == []


def test_prects_zero_unchanged_and_bounds():
    P = schema.Plan(_raw(MEAS))
    pre = gen_phys.clock_phase_tcl(P, "src")
    assert "-early -clock clk 0.0000" in pre and "-12.0000" not in pre
    assert "-61.0000" in gen_phys.clock_phase_tcl(P, "src", before_cts=True)
    with pytest.raises(ValueError, match="per_port_ps"):
        gen_phys.tap_window_port_table(schema.Plan(_raw({"src": {"clk": 300}})), "src")


def test_core_tap_takes_its_port_window(monkeypatch):
    P = schema.Plan(_raw({"src": dict(MEAS["src"], clk_c0=17)}))
    monkeypatch.setattr(gen_phys, "core_tap_rows", lambda p, t, corner="TT": [("clk_c0", "u", "*", 50.0, 300.0)])
    assert gen_phys.core_tap_window_tcl(P, "src") == "set_clock_latency -source -early -clock clk -67.0000 [get_ports clk_c0]\n"


def _tap(part, port, late, early, node):
    return {"port": f"t_{part}__{port}", "part": part, "late_ps": late, "early_ps": early, "cppr_node": node,
            "slew_ps": 20.0}


def test_need_from_measured_arrivals_with_cppr_credit():
    """same-root taps (one cppr_node) get the root's CPPR credit; cross-root taps of one partition only the die root's."""
    rows = [_tap("a0", "clk_t1", 300.0, 280.0, "ra"), _tap("a0", "clk_t2", 340.0, 320.0, "ra"),
            _tap("a0", "clk_t3", 330.0, 310.0, "rb"), _tap("b0", "clk_t1", 310.0, 300.0, "rc")]
    taps = {r["port"]: r for r in rows}
    rng = {"h": 2.0, "ra": 15.0, "rb": 15.0, "rc": 5.0}
    plan = {"partitions": [{"name": "a0", "type": "T"}, {"name": "b0", "type": "T"}], "ports": []}
    pairs, _cov = DSR.build_pairs(plan, taps)
    nd = DSR.kit_port_needs([pairs["intra"], pairs["intra_cross_region"]], taps, rng)
    # clk_t1 early 280: same-root t2 late 340 - 280 - 15 = 45; cross-root t3 late 330 - 280 - 2 = 48 -> 48
    assert nd[("a0", "clk_t1")] == pytest.approx(48.0)
    # clk_t2 early 320: t1 300 - 320 - 15 < 0; t3 (cross) 330 - 320 - 2 = 8
    assert nd[("a0", "clk_t2")] == pytest.approx(8.0)
    # clk_t3 early 310 (root rb, alone): t1 300-310-2 < 0, t2 340-310-2 = 28
    assert nd[("a0", "clk_t3")] == pytest.approx(28.0)
    assert nd[("b0", "clk_t1")] == 0.0            # single tap: same-port pairs only (OpenSTA CRPR at the port)
    # without the root credit the same-root pair would need 60, i.e. CPPR is what keeps it at 45
    nd0 = DSR.kit_port_needs([pairs["intra"]], taps, {"h": 0.0})
    assert nd0[("a0", "clk_t1")] == pytest.approx(60.0)
    tab = DSR.kit_window_table([nd, {("a0", "clk_t2"): 9.4}], plan)
    assert tab == {"T": {"clk_t1": 48.0, "clk_t2": 10.0, "clk_t3": 28.0}}


def test_die_check_reads_per_port_windows():
    plan = {"partitions": [{"name": "a0", "type": "T"}, {"name": "b0", "type": "U"}], "die": {"period_ps": 833}}
    pc = {"seam_hold": {"sender_ps": 0, "seam_ps": 40}, "tap_window": {"window_ps": 100, "related_pair_ps": 100, "per_port_ps": {"T": {"clk_t1": 48}}}}
    w = DSR.kit_windows(pc, None, plan)["intra"]
    assert w["ps"] == 100.0 and w["per_port"] == {"a0": {"clk_t1": 48.0}}
    assert "per port" in w["basis"]
    assert "per_port" not in DSR.kit_windows({k: (dict(v, per_port_ps={}) if k == "tap_window" else v)
                                              for k, v in pc.items()}, None, plan)["intra"]


def test_die_contract_bound_uses_the_early_side_port_window():
    reg = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=46.5, setup_ps=5.6, hold_ps=22.2)
    taps = {"t_p__clk_t1": dict(part="p", late_ps=1000.0, early_ps=990.0, cppr_node="h0"),
            "t_p__clk_t2": dict(part="p", late_ps=1050.0, early_ps=1040.0, cppr_node="h0")}
    pairs = [("t_p__clk_t1", "t_p__clk_t2", "p"), ("t_p__clk_t2", "t_p__clk_t1", "p")]
    # t1 early side: 1050 - 990 - 10 = 50; its measured window 50 -> PASS although the flat W is 20
    hw = dict(ps=20.0, basis="t", per_port={"p": {"clk_t1": 50.0, "clk_t2": 0.0}})
    kc = DSR.time_class(pairs, taps, {"h0": 10.0}, reg, 20.0, 833.333, 60.0, 25.0, hold_window=hw)["kit_contract_hold"]
    assert kc["verdict"] == "PASS" and kc["window_mode"] == "per_port" and kc["worst_hold_bound_ps"] == 0.0
    hw["per_port"]["p"]["clk_t1"] = 45.0
    kc = DSR.time_class(pairs, taps, {"h0": 10.0}, reg, 20.0, 833.333, 60.0, 25.0, hold_window=hw)["kit_contract_hold"]
    assert kc["verdict"] == "FAIL" and kc["worst_hold_bound_ps"] == -5.0
    # a port missing from the table falls back to the region / flat W (20): FAIL on t1 again
    hw["per_port"]["p"] = {"clk_t2": 0.0}
    kc = DSR.time_class(pairs, taps, {"h0": 10.0}, reg, 20.0, 833.333, 60.0, 25.0, hold_window=hw)["kit_contract_hold"]
    assert kc["verdict"] == "FAIL" and kc["window_ps"] == 20.0
