"""DIE-HEAD-36 (COORD 10-29 21:11 ruling (3)): source-synchronous landing-ring inputs are timed against the forwarded
write clock that captures them (fclk_in_<b>), not vclk; sign-off scopes its insertion census and boundary-hold overlay
the same way (pinreg_measure.tcl flop set).  Kits without a forwarded input ring stay byte-identical."""
import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import landing_contract as LC  # noqa: E402
import schema  # noqa: E402
import signoff  # noqa: E402
import sdc_lint  # noqa: E402
from test_sdc_lint import TINY, _errs  # noqa: E402


def _ring_kit(band=True, status=True):
    raw = copy.deepcopy(TINY)
    P0 = schema.Plan(raw)
    tn = next(t for t in P0.types if not P0.types[t].get("hard") and any(p["type"] == t for p in P0.parts.values())
              and any(b["dir"] == "in" for b in P0.types[t].get("buses", [])))
    bus = next(b for b in P0.types[tn]["buses"] if b["dir"] == "in")
    b = gen_rtl.sv_id(bus["name"])
    x, y = raw["partition_types"][tn]["clock"]["tap_um"]
    ck = raw["partition_types"][tn]["clock"]
    ck["edge_clocks"] = [{"port": f"fclk_in_{b}", "tap_um": [x + 17.28, y + 8.64]}]
    pins = [dict(name=f"fclk_in_{b}", dir="in", kind="clock", epoch=False, layer="M5", xy_um=[x + 17.28, y + 8.64])]
    if status:
        pins += [dict(name=f"cland_dn_{k}_{b}", dir="in", kind="ctl", epoch=False, layer="M5",
                      xy_um=[x + 17.28, y + 17.28 + 4.32 * i]) for i, k in enumerate(("ready", "fault"))]
    ck["landing_contract"] = {"pins": pins}
    if band:
        ck["landing_contract"]["bands"] = {b: {"width": int(bus.get("width", 1)), "instance": f"u_cland_{b}"}}
    P = schema.Plan(raw)
    return P, tn, b, int(bus.get("width", 1))


def test_ring_inputs_timed_against_forwarded_clock():
    P, tn, b, w = _ring_kit()
    txt = gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))
    sel = b + ("[*]" if w > 1 else "")
    ck = f"fclk_in_{b}"
    tail = txt.split(LC.RING_INPUTS_TAG, 1)[1]
    assert tail.splitlines()[0].split() == [ck, sel, f"cland_dn_ready_{b}", f"cland_dn_fault_{b}"]
    per = gen_phys.t_lib(P.die["period_ps"])
    mx = gen_phys.IO_BUDGET * per + gen_phys.t_lib(gen_phys.tap_window_io_shift(P)[0])
    mn = gen_phys.t_lib(gen_phys.hold_in_min_ps(P))
    for s in (sel, f"cland_dn_ready_{b}", f"cland_dn_fault_{b}"):
        assert f"set_input_delay -max {mx:.4f} -clock {ck} [get_ports {{{s}}}]" in tail
        assert f"set_input_delay -min {mn:.4f} -clock {ck} [get_ports {{{s}}}]" in tail
    # the ring lines come LAST: OpenSTA drops a port's other-clock delays only when the new clock is set after them
    last_vclk = max(i for i, ln in enumerate(txt.splitlines()) if ln.startswith("set_input_delay") and "vclk" in ln)
    first_ring = min(i for i, ln in enumerate(txt.splitlines()) if ln.startswith("set_input_delay") and ck in ln)
    assert first_ring > last_vclk
    # the kit SDC still lints clean (same values, re-referenced)
    assert _errs(txt, sdc_lint.kit_context(P, tn)) == []
    assert signoff.fwd_ring_inputs(txt) == [(ck, [sel, f"cland_dn_ready_{b}", f"cland_dn_fault_{b}"])]


def test_no_band_or_no_status_pins():
    P, tn, b, w = _ring_kit(band=False)
    assert LC.ring_input_sdc(P, tn) == "" and LC.RING_INPUTS_TAG not in gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))
    P, tn, b, w = _ring_kit(status=False)
    assert LC.ring_input_ports(P, tn) == [(f"fclk_in_{b}", [b + ("[*]" if w > 1 else "")])]


def test_band_without_input_port_fails_closed():
    P, tn, b, w = _ring_kit()
    c = P.types[tn]["clock"]["landing_contract"]
    c["bands"] = {"no_such_bus": {}}
    c["pins"].append(dict(name="fclk_in_no_such_bus", dir="in", kind="clock", epoch=False, layer="M5", xy_um=[0, 0]))
    with pytest.raises(ValueError, match="no input port"):
        LC.ring_input_ports(P, tn)


RING = [("fclk_in_a", ["a_i[*]", "cland_dn_ready_a_i"])]


@pytest.mark.parametrize("corner,mode", [("tt", "sdc"), ("ff", "rebind"), ("ff", "pin-flop-mean")])
def test_signoff_session_scopes_forwarded_ring(corner, mode):
    plain = signoff.session_tcl(corner, [], "x.spef", ff_vclk=mode)
    assert plain == signoff.session_tcl(corner, [], "x.spef", ff_vclk=mode, fwd_ring=None)
    assert plain == signoff.session_tcl(corner, [], "x.spef", ff_vclk=mode, fwd_ring=[])
    assert "so_fwd" not in plain
    t = signoff.session_tcl(corner, [], "x.spef", ff_vclk=mode, fwd_ring=RING, hold_in_min=-40.0,
                            hold_in_min_ports={"a_i": -55.0, "b_i": -30.0})
    # insertion census = local-clock pin flops only (pinreg_measure.tcl set): forwarded ring writers skipped
    n_regs = t.count("foreach p [all_registers -clock_pins] { if {[llength [get_property $p clocks]] == 1 && "
                     "[get_full_name [lindex [get_property $p clocks] 0]] in $::so_fwd_clks} continue; dict set so_")
    assert n_regs == (2 if "FF_VCLK applied" in t else 1)
    assert "set so_fwd_clks {fclk_in_a}" in t
    assert "set so_din [lmap p $so_din {if {[get_full_name $p] in $so_fwd_in} continue; set p}]" in t
    # the ring inputs leave the vclk overlay and keep their own clock, same contract value (per-port where given)
    assert "set_input_delay -min -55 -clock fclk_in_a [get_ports {a_i[*]}]" in t
    assert "set_input_delay -min -40 -clock fclk_in_a [get_ports {cland_dn_ready_a_i}]" in t
    assert "[get_ports {a_i[*]}]" not in t.split("set_input_delay -min -55 -clock fclk_in_a")[0].split("@IN_MIN_PORTS@")[-1].replace("so_fwd_in [lmap p [get_ports {a_i[*] cland_dn_ready_a_i}]", "")
    assert "-clock [lindex $so_vclk 0] [get_ports {b_i[*]}]" in t
    # INPUTS (sdc_lint context) is printed before the ring filter: the lint still sees every input
    assert t.index("so INPUTS") < t.index("set so_fwd_clks")
