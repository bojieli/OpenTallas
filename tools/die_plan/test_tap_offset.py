"""R-CLOCK-7 (FABLE-REVIEW-CLK 1b, COORD 11-14): kit tap arrival offsets (plan clock.tap_offset) in place of an absolute window:
set_clock_latency -source -early (o - u) / -late (o + u) per tap port, TT in the SDC, FF in the corner overlay; a type without a
row keeps today's window; die_sta_related --kit-offset-out writes the table."""
import json
from pathlib import Path

import die_sta_related as DSR
import gen_phys
import schema

HERE = Path(__file__).parent
ROW = {"clk": {"TT": 0.0, "FF": 0.0, "tol": 10.0}, "clk_t1": {"TT": -12.5, "FF": -14.0, "tol": 10.0},
       "clk_t2": {"TT": 20.0, "FF": 18.0, "tol": 15.0}}


def _raw(offsets=None, window=80.0):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["tap_window"] = dict(window_ps=window, related_pair_ps=window, note="flat W")
    if offsets is not None:
        raw["clock"]["tap_offset"] = dict(per_port_ps={"src": offsets}, source="test", proof="x")
    return raw


def _sdc(P, tn="src"):
    return gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))


def test_schema():
    assert schema.validate(_raw(ROW)) == []
    assert schema.validate(_raw({"clk": {"TT": 0, "FF": 0}}))        # tol required


def test_emits_offsets_per_port_and_span():
    P = schema.Plan(_raw(ROW))
    s = _sdc(P)
    assert "set_clock_latency -source -early -clock clk -10.0000 [get_ports {clk}]" in s
    assert "set_clock_latency -source -late -clock clk 10.0000 [get_ports {clk}]" in s
    assert "set_clock_latency -source -early -clock clk -22.5000 [get_ports {clk_t1}]" in s
    assert "set_clock_latency -source -late -clock clk -2.5000 [get_ports {clk_t1}]" in s
    assert "set_clock_latency -source -early -clock clk 5.0000 [get_ports {clk_t2}]" in s
    assert "set_clock_latency -source -late -clock clk 35.0000 [get_ports {clk_t2}]" in s
    # span = max(o+u) - min(o-u) = 35 - (-22.5) = 57.5 (TT), 33 - (-24) = 57 (FF) -> 57.5; the IO shift follows it
    assert gen_phys.tap_window_ps(P, "src") == 57.5
    assert gen_phys.tap_window_io_shift(P, "src") == (-57.5, 57.5)
    assert "-80.0000" not in s


def test_port_without_row_takes_the_window_span():
    row = {k: v for k, v in ROW.items() if k != "clk_t2"}
    P = schema.Plan(_raw(row))
    s = _sdc(P)
    w = gen_phys.tap_window_ps(P, "src")
    assert f"set_clock_latency -source -early -clock clk {-w:.4f} [get_ports {{clk_t2 " in s or f"{-w:.4f} [get_ports {{" in s


def test_ff_overlay_has_ff_values():
    P = schema.Plan(_raw(ROW))
    ff = gen_phys.core_tap_ff_sdc(P, "src")
    assert "set_clock_latency -source -early -clock clk -24.0000 [get_ports {clk_t1}]" in ff
    assert "set_clock_latency -source -late -clock clk 33.0000 [get_ports {clk_t2}]" in ff


def test_type_without_row_unchanged():
    base = schema.Plan(_raw(None))
    other = _raw({"clk": {"TT": 0, "FF": 0, "tol": 10}})
    other["clock"]["tap_offset"]["per_port_ps"] = {"not_src": other["clock"]["tap_offset"]["per_port_ps"]["src"]}
    assert _sdc(schema.Plan(other)) == _sdc(base)
    assert gen_phys.tap_offset_table(schema.Plan(other), "src") == {}


def test_kit_offset_table():
    taps = {}
    for part, shift in (("p1", 0.0), ("p2", 6.0)):
        for port, a in (("clk", 100.0), ("clk_t1", 90.0), ("clk_t2", 130.0)):
            taps[f"t_{part}__{port}"] = {"part": part, "late_ps": a + shift + 1, "early_ps": a + shift - 1}
    arr = {"TT": DSR.kit_offset_arrivals(taps), "FF": {k: v * 0.9 for k, v in DSR.kit_offset_arrivals(taps).items()}}
    tab = DSR.kit_offset_table(arr, {"partitions": [{"name": "p1", "type": "src"}, {"name": "p2", "type": "src"}]})
    # median glue of a partition = 100 (clk); per instance o = 0 / -10 / +30 for both shifts: tol floor 10
    assert tab["src"]["clk_t1"]["TT"] == -10.0 and tab["src"]["clk_t2"]["TT"] == 30.0 and tab["src"]["clk"]["tol"] == 10.0
    assert tab["src"]["clk_t2"]["FF"] == 27.0
