"""DIE-HEAD-21: plan clock.edge_clocks[].source_latency_ps -> forwarded edge clock source latency per corner.

TT early/late in constraint.sdc, FF early/late in the core_taps_ff.sdc corner overlay (vclk_corner.tcl, postcts FF
gate, sign-off FF); absent field = byte-identical kit SDC / lint context."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

import gen_phys as G
import schema as S
import sdc_lint

HERE = Path(__file__).resolve().parent
TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
SL = {"tt": {"early": 158.1, "late": 163.5}, "ff": {"early": 123.0, "late": 127.5}, "basis": "DH20 fwd_out + wire"}


def _raw(sl=None):
    raw = copy.deepcopy(TINY)
    P0 = S.Plan(raw)
    tn = next(t for t in P0.types if not P0.types[t].get("hard") and any(p["type"] == t for p in P0.parts.values()))
    x, y = raw["partition_types"][tn]["clock"]["tap_um"]
    e = {"port": "fclk_in_i", "tap_um": [x + 17.28, y + 8.64], "note": "source-forwarded ring write clock"}
    if sl is not None:
        e["source_latency_ps"] = copy.deepcopy(sl)
    raw["partition_types"][tn]["clock"]["edge_clocks"] = [e]
    return raw, tn


def _sdc(raw, tn):
    P = S.Plan(raw)
    return P, G.sdc(P, tn, G.type_pins(P, tn))


def test_absent_field_byte_identical():
    raw0, tn = _raw()
    P0, s0 = _sdc(raw0, tn)
    assert G.edge_clock_latency(P0, tn) == [] and G.edge_clock_latency_tcl(P0, tn, "ff") == ""
    assert "OT_CORE_TAP_CORNER_FILE" not in s0 and "-early" not in s0
    assert "edge_clock_latency_ps" not in sdc_lint.kit_context(P0, tn)
    # the plan without edge clocks at all: same text as before the change (no stray line)
    P1 = S.Plan(TINY)
    tn1 = next(t for t in P1.types if not P1.types[t].get("hard"))
    assert "get_clocks fclk" not in G.sdc(P1, tn1, G.type_pins(P1, tn1))


def test_schema_accepts_and_rejects():
    raw, _tn = _raw(SL)
    assert S.validate(raw) == []
    bad = copy.deepcopy(SL)
    del bad["ff"]
    raw, _tn = _raw(bad)
    assert S.validate(raw)
    bad = copy.deepcopy(SL)
    bad["tt"]["min"] = 1.0
    raw, _tn = _raw(bad)
    assert S.validate(raw)


def test_tt_in_sdc_ff_in_overlay_and_lint(tmp_path):
    raw0, tn = _raw()
    _P0, s0 = _sdc(raw0, tn)
    raw, tn = _raw(SL)
    P, s = _sdc(raw, tn)
    tt = ("set_clock_latency -source -early 158.1000 [get_clocks fclk_in_i]\n"
          "set_clock_latency -source -late 163.5000 [get_clocks fclk_in_i]\n")
    assert tt in s
    assert s.index("create_clock -name fclk_in_i") < s.index(tt)
    assert "# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n" in s
    # only the edge latency block + marker were added
    added = [ln for ln in s.splitlines() if ln not in s0.splitlines()]
    assert len(added) == 4 and all("fclk_in_i" in ln or "OT_CORE_TAP_CORNER_FILE" in ln for ln in added)
    ff = G.core_tap_ff_sdc(P, tn) + G.edge_clock_latency_tcl(P, tn, "ff")
    assert "set_clock_latency -source -early 123.0000 [get_clocks fclk_in_i]" in ff
    assert "set_clock_latency -source -late 127.5000 [get_clocks fclk_in_i]" in ff
    assert "158.1" not in ff.replace("# ", "") or "-early 158.1" not in ff
    ctx = sdc_lint.kit_context(P, tn)
    assert ctx["edge_clock_latency_ps"] == {"fclk_in_i": [158.1, 163.5]}
    assert sdc_lint.lint(s, **ctx) == []
    # lint: wrong value, missing line, and the same lines without the plan field all fail closed
    assert any("fclk_in_i" in e for e in sdc_lint.lint(s.replace("-late 163.5000", "-late 170.0000"), **ctx))
    assert any("fclk_in_i" in e for e in sdc_lint.lint(s.replace(tt, ""), **ctx))
    bare = {k: v for k, v in ctx.items() if k != "edge_clock_latency_ps"}
    assert any("fclk_in_i" in e for e in sdc_lint.lint(s, **bare))
    # a single-valued real clock latency stays forbidden
    one = s.replace(tt, "set_clock_latency -source 158.1000 [get_clocks fclk_in_i]\n")
    assert any("real clock fclk_in_i" in e for e in sdc_lint.lint(one, **ctx))


def test_early_above_late_rejected():
    bad = copy.deepcopy(SL)
    bad["ff"]["early"] = 130.0
    raw, tn = _raw(bad)
    with pytest.raises(ValueError, match="early <= late"):
        G.edge_clock_latency(S.Plan(raw), tn)


def test_tap_window_conflict_rejected(monkeypatch):
    raw, tn = _raw(SL)
    P = S.Plan(raw)
    monkeypatch.setattr(G, "tap_window_ps", lambda _P: 20.0)    # a plan clock.tap_window of 20 ps
    with pytest.raises(ValueError, match="tap_window"):
        G.edge_clock_latency(P, tn)


def test_vclk_corner_switches_edge_latency(tmp_path):
    raw, tn = _raw(SL)
    P, s = _sdc(raw, tn)
    (tmp_path / "vclk_corner.tcl").write_text((HERE / "vclk_corner.tcl").read_text())
    (tmp_path / "constraint.sdc").write_text(s)
    (tmp_path / "core_taps_ff.sdc").write_text(G.core_tap_ff_sdc(P, tn) + G.edge_clock_latency_tcl(P, tn, "ff"))
    fixture = r"""
proc get_ports {p} {return $p}
proc get_clocks {p} {return $p}
proc set_clock_latency {args} {puts "LATENCY [join $args { }]"}
proc read_sdc {p} {uplevel #0 [list source $p]}
source vclk_corner.tcl
puts FF
ot_core_tap_bind ff
puts TT
ot_core_tap_bind tt
"""
    out = subprocess.run(["tclsh"], input=fixture, text=True, cwd=tmp_path, capture_output=True, check=True).stdout
    ffp, ttp = out.split("TT\n")
    assert "LATENCY -source -early 123.0000 fclk_in_i" in ffp and "LATENCY -source -late 127.5000 fclk_in_i" in ffp
    assert "LATENCY -source -early 158.1000 fclk_in_i" in ttp and "LATENCY -source -late 163.5000 fclk_in_i" in ttp
    assert "vclk" not in ttp     # the vclk TT line is ot_vclk_bind's, not re-applied here


def test_write_type_kit_writes_overlay(tmp_path):
    raw, tn = _raw(SL)
    P = S.Plan(raw)
    kd = tmp_path / "kit"
    try:
        G.write_type_kit(P, tn, kd, [], trial=True)
    except Exception as e:      # kit writer needs RTL / platform files beyond this unit; check the SDC pair only
        pytest.skip(f"write_type_kit not runnable on TINY: {e}")
    k = next(p for p in [kd, kd / tn] if (p / "constraint.sdc").is_file())
    assert "-early 123.0000 [get_clocks fclk_in_i]" in (k / "core_taps_ff.sdc").read_text()
