"""S81-RINGHOLD-3 (COORD 10-31 06:51, ring-write hold variant (b)): a forwarded ring write clock carries no plan tap
window (launch and capture are the same forwarded edge at one port; the window cost 180 of 321 ps on S81 t29), and an
opt-in measured sender min (clock.ring_hold.sender_ps) replaces the seam fallback on the ring inputs in the kit SDC,
the post-CTS hold gate and the sign-off overlay.  Kits without a forwarded ring stay byte-identical."""
import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import landing_contract as LC  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402
import signoff  # noqa: E402
from test_ring_input_sdc import _ring_kit  # noqa: E402
from test_sdc_lint import _errs  # noqa: E402


def _windowed(P, sender=None):
    raw = copy.deepcopy(P.raw)
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["tap_window"] = dict(window_ps=80)
    if sender is not None:
        raw["clock"]["ring_hold"] = dict(sender_ps=sender)
    return schema.Plan(raw)


def _sdc(P, tn):
    return gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))


def test_ring_clock_has_no_window_and_no_io_shift():
    P0, tn, b, w = _ring_kit()
    P = _windowed(P0)
    ck = f"fclk_in_{b}"
    s = _sdc(P, tn)
    assert gen_phys.ring_writer_clocks(P, tn) == {ck}
    assert f"[get_ports {{{ck}}}]" not in "".join(ln for ln in s.splitlines() if "set_clock_latency" in ln)
    ports = " ".join(n for n, _x, _y in gen_phys.clock_pins(P, tn))
    assert f"set_clock_latency -source -early -clock clk -80.0000 [get_ports {{{ports}}}]" in s      # taps keep it
    sel = b + ("[*]" if w > 1 else "")
    per = gen_phys.t_lib(P.die["period_ps"])
    tail = s.split(LC.RING_INPUTS_TAG, 1)[1]
    assert f"set_input_delay -max {gen_phys.IO_BUDGET * per:.4f} -clock {ck} [get_ports {{{sel}}}]" in tail
    assert f"set_input_delay -min {gen_phys.t_lib(gen_phys.hold_in_min_ps(P)):.4f} -clock {ck} [get_ports {{{sel}}}]" in tail
    assert LC.RING_MIN_TAG not in s
    ctx = sdc_lint.kit_context(P, tn)
    assert ctx["ring_clock_ports"] == [ck]
    assert _errs(s, ctx) == []
    # tampering: a window put back on the ring clock is a lint error (not a window clock port)
    bad = s + f"set_clock_latency -source -early -clock {ck} -80.0000 [get_ports {{{ck}}}]\n"
    assert any("not a window clock port" in e for e in _errs(bad, ctx))


def test_edge_clock_without_ring_keeps_window():
    P0, tn, b, w = _ring_kit(band=False)
    P = _windowed(P0)
    assert gen_phys.ring_writer_clocks(P, tn) == set()
    assert f"set_clock_latency -source -early -clock fclk_in_{b} -80.0000 [get_ports {{fclk_in_{b}}}]" in _sdc(P, tn)
    assert "ring_clock_ports" not in sdc_lint.kit_context(P, tn)


def test_ring_hold_sender_min_everywhere():
    P0, tn, b, w = _ring_kit()
    P = _windowed(P0, sender=73.2)
    ck = f"fclk_in_{b}"
    s = _sdc(P, tn)
    sel = b + ("[*]" if w > 1 else "")
    for x in (sel, f"cland_dn_ready_{b}", f"cland_dn_fault_{b}"):
        assert f"set_input_delay -min 73.2000 -clock {ck} [get_ports {{{x}}}]" in s
    assert s.count(f"{LC.RING_MIN_TAG} 73.2000\n") == 1
    assert s.index(LC.RING_MIN_TAG) < s.index(LC.RING_INPUTS_TAG)
    assert _errs(s, sdc_lint.kit_context(P, tn)) == []
    assert signoff.fwd_ring_min(s) == 73.2 and signoff.fwd_ring_min("x\n") is None
    ring = signoff.fwd_ring_inputs(s)
    t = signoff.session_tcl("ff", [], "x.spef", ff_vclk="sdc", fwd_ring=ring, hold_in_min=-40.0,
                            fwd_ring_min=signoff.fwd_ring_min(s))
    assert f"set_input_delay -min 73.2 -clock {ck} [get_ports {{{sel}}}]" in t
    t0 = signoff.session_tcl("ff", [], "x.spef", ff_vclk="sdc", fwd_ring=ring, hold_in_min=-40.0)
    assert f"set_input_delay -min -40 -clock {ck} [get_ports {{{sel}}}]" in t0


def test_ring_hold_schema_rejects_extra_keys():
    P0, tn, b, w = _ring_kit()
    raw = copy.deepcopy(P0.raw)
    raw["clock"]["ring_hold"] = dict(sender_ps=73.2)
    assert not [e for e in schema.validate_structure(raw) if "ring_hold" in e]
    raw["clock"]["ring_hold"]["bogus"] = 1
    assert [e for e in schema.validate_structure(raw) if "ring_hold" in e or "bogus" in e]


@pytest.mark.parametrize("tag,want", [("", "-40"), ("# OT_FWD_RING_MIN 73.2000\n", "73.2000")])
def test_hold_gate_applies_ring_min(tmp_path, tag, want):
    import test_hold_gate_ring as T
    r = T._run(tmp_path, "create_clock -name clk\n" + tag + "# OT_FWD_RING_INPUTS fclk_in_t_i t_i[*] cland_dn_ready_t_i\n")
    assert r.returncode == 0, r.stderr
    sid = [ln for ln in r.stdout.splitlines() if ln.startswith("SID")]
    assert "SID -min -40 -clock vclk {a b}" in sid                      # the vclk overlay is unchanged
    assert f"SID -min {want} -clock fclk_in_t_i {{{{t_i[0]}} {{t_i[1]}}}}" in sid
    assert f"OT_HOLD_GATE forwarded ring inputs 3 on 1 clock(s), min {want}" in r.stdout
