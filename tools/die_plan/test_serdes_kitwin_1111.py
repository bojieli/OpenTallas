"""SERDES-KITWIN-1111: physical/die_plan/s81/events/serdes_kitwin_1111/delta_serdes_kitwin_1111.py fills the plan's
clock.tap_window.per_port_ps for the serdes types (measured + 20 ps, cap 208, no 116 clip), through the existing KW-FIX-4-SDC
mechanism (gen_phys.tap_window_port_table).  Byte-identical outside the written types."""
import importlib.util
import json
from pathlib import Path

import pytest

import gen_phys
import schema

HERE = Path(__file__).parent
EV = HERE.parent.parent / "physical/die_plan/s81/events/serdes_kitwin_1111/delta_serdes_kitwin_1111.py"
_spec = importlib.util.spec_from_file_location("dsk", EV)
DSK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DSK)

PORTS = ["clk", "clk_t1", "clk_t2", "clk_t3", "clk_t4", "clk_t5", "clk_t6", "clk_t7", "clk_t8"]


def _plan_text(per_port=None, window=80.0):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    tw = dict(window_ps=window, note="flat W", per_type_ps={"src": 70})
    if per_port is not None:
        tw["per_port_ps"] = per_port
    raw["clock"]["tap_window"] = tw
    return json.dumps(raw, indent=1) + "\n"


class A:
    margin, cap, flag, prefix = 20.0, 208.0, 116.0, "src"


def _tab(m):
    return dict(per_port_ps=m, plan_sha256="abc", corners=["TT", "FF"], _name="t.json", _sha256="0" * 64)


MEAS = {"src": {p: 10 * i for i, p in enumerate(PORTS)}}          # 0..80


def test_margin_added_and_zero_measured_gets_margin():
    s, rep, new = DSK.build(_plan_text(), _tab(MEAS), A)
    assert new["src"]["clk"] == 20 and new["src"]["clk_t8"] == 100
    assert rep["ports_written"] == len(PORTS) and rep["types_unmeasured_keep_flat"] == {}
    P = schema.Plan(json.loads(s))
    assert gen_phys.tap_window_port_table(P, "src")["clk_t3"] == 50.0


def test_over_116_is_kept_plus_margin_not_clipped():
    m = {"src": dict(MEAS["src"], clk_t5=131.0, clk_t6=118)}
    s, rep, new = DSK.build(_plan_text(), _tab(m), A)
    assert new["src"]["clk_t5"] == 151 and new["src"]["clk_t6"] == 138
    assert rep["ports_measured_over_flag"]["src"]["clk_t5"] == [131.0, 151.0] and not rep["ports_clamped_to_cap"]


def test_cap_208_clamps_and_reports():
    m = {"src": dict(MEAS["src"], clk_t5=200.0)}
    _s, rep, new = DSK.build(_plan_text(), _tab(m), A)
    assert new["src"]["clk_t5"] == 208 and rep["ports_clamped_to_cap"]["src"]["clk_t5"] == [200.0, 220.0]


def test_type_without_measured_port_keeps_flat_and_is_listed():
    text = _plan_text()
    s, rep, new = DSK.build(text, _tab({"other": {"clk": 5}}), A)
    assert s == text and new == {} and rep["types_unmeasured_keep_flat"] == {"src": 70}


def test_text_outside_the_block_is_unchanged_and_note_appended():
    text = _plan_text()
    s, _rep, _new = DSK.build(text, _tab(MEAS), A)
    a, b = json.loads(text), json.loads(s)
    assert b["clock"]["tap_window"].pop("note").startswith("flat W SERDES-KITWIN-1111")
    b["clock"]["tap_window"].pop("per_port_ps")
    a["clock"]["tap_window"].pop("note")
    assert a == b


def test_existing_per_port_block_gets_the_new_types_appended():
    text = _plan_text(per_port={"zzz": {"clk": 7}})
    s, _rep, new = DSK.build(text, _tab(MEAS), A)
    d = json.loads(s)["clock"]["tap_window"]["per_port_ps"]
    assert d["zzz"] == {"clk": 7} and d["src"]["clk"] == 20
    a = s.index(" SERDES-KITWIN-1111")                         # the appended note is the only earlier change
    assert (s[:a] + s[s.index('"', a):]).startswith(text[:text.index('"zzz"')])


def test_idempotent_and_conflicting_entry_refused():
    s, _r, _n = DSK.build(_plan_text(), _tab(MEAS), A)
    s2, _r2, new2 = DSK.build(s, _tab(MEAS), A)
    assert new2 == {} and s2 == s                              # second run adds nothing
    with pytest.raises(SystemExit, match="different"):
        DSK.build(s, _tab({"src": dict(MEAS["src"], clk=99)}), A)


def test_sdc_uses_the_per_port_lines_and_flat_when_absent():
    text = _plan_text()
    P0 = schema.Plan(json.loads(text))
    sdc0 = gen_phys.sdc(P0, "src", gen_phys.type_pins(P0, "src"))
    s, _r, _n = DSK.build(text, _tab(MEAS), A)
    P1 = schema.Plan(json.loads(s))
    sdc1 = gen_phys.sdc(P1, "src", gen_phys.type_pins(P1, "src"))
    assert "-70.0000" in sdc0 and "MEASURED per port" not in sdc0
    assert "MEASURED per port" in sdc1 and "FALLBACK" not in sdc1 and "-70.0000 [get_ports {clk clk_t1" not in sdc1
    assert "set_clock_latency -source -early -clock clk -100.0000 [get_ports {clk_t8}]" in sdc1
    # no table for the type: the SDC is byte-identical
    s2, _r2, new2 = DSK.build(text, _tab({"other": {"clk": 1}}), A)
    P2 = schema.Plan(json.loads(s2))
    assert new2 == {} and gen_phys.sdc(P2, "src", gen_phys.type_pins(P2, "src")) == sdc0
