"""PINREG-TAPS 11-23 (FABLE-RC-REVIEW row 33): clock.pinreg_taps hangs boundary pin-register chunks only on the named
pin-face taps and evicts every other sink from them (clock_taps.tcl last pass); gen_phys.pinreg_tap_exports."""
import pytest

from tools.die_plan import gen_phys
from tools.die_plan.test_clock_taps_groups import run

PINRE = "set ::env(OT_PINREG_TAP_RE) {(?:^|[/.])(u_b(?:in|out)_[A-Za-z0-9]+_[io][0-9]+)[/.](?:q_([0-9]+))?}"


def body():
    # pin registers near clk (x 100-160) must go to the pin-face tap clk_t1; fillers near clk_t1 must leave it
    s = ''.join(f'mkflop u_bin_x_i0/q_{b} {100 + b}\n' for b in range(4))
    s += 'mkflop u_bin_x_i0/eq 120\n'
    s += ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120))
    return s


def test_pin_registers_on_face_tap_only(tmp_path):
    p = run(tmp_path, body(), env=PINRE + '\nset ::env(OT_PINREG_TAPS) clk_t1\nset ::env(OT_PINREG_CHUNK) 2')
    assert p.returncode == 0, p.stderr
    out = p.stdout
    for b in range(4):
        assert f'NET ck_u_bin_x_i0/q_{b} nt1' in out, out
    assert 'NET ck_u_bin_x_i0/eq nt1' in out
    for i in range(120):
        assert f'NET ck_f{i} nclk' in out, out
    assert 'OT_PINREG_TAPS 1 pin-face taps, 3 register chunks' in out and '60 other sinks evicted' in out, out


def test_default_off(tmp_path):
    p = run(tmp_path, body(), env=PINRE)
    assert p.returncode == 0, p.stderr
    assert 'OT_PINREG_TAPS' not in p.stdout
    assert 'NET ck_u_bin_x_i0/q_0 nclk' in p.stdout and 'NET ck_f100 nt1' in p.stdout


def test_unknown_port_and_no_match_fail(tmp_path):
    p = run(tmp_path, body(), env=PINRE + '\nset ::env(OT_PINREG_TAPS) clk_t9')
    assert p.returncode != 0 and 'unknown or non-grid clock port: clk_t9' in p.stderr
    p = run(tmp_path, ''.join(f'mkflop f{i} {0 if i < 60 else 1000}\n' for i in range(120)),
            env=PINRE + '\nset ::env(OT_PINREG_TAPS) clk_t1')
    assert p.returncode != 0 and 'no pin-register clock pins match' in p.stderr


def _t(pr):
    return {"clock": {"taps": [{"name": "clk", "xy": [0, 0]}], "added_taps": [{"name": "clk_t900", "xy": [5, 1]}],
                      "pinreg_taps": pr}}


def test_exports():
    assert gen_phys.pinreg_tap_exports({"clock": {}}) == []
    assert gen_phys.pinreg_tap_exports(_t({"ports": ["clk_t900"], "chunk": 64})) == [
        "export OT_PINREG_TAPS = clk_t900", "export OT_PINREG_CHUNK = 64"]
    with pytest.raises(ValueError):
        gen_phys.pinreg_tap_exports(_t({"ports": ["clk_t901"]}))
    with pytest.raises(ValueError):
        gen_phys.pinreg_tap_exports(_t({"ports": ["clk", "clk_t900"]}))
    with pytest.raises(ValueError):
        gen_phys.pinreg_tap_exports(_t({"ports": ["clk_t900"], "re": "a b(c)"}))
