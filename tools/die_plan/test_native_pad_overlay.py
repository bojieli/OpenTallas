"""Native recovered-pad min/max remain associated with their existing clock through FF overlays."""
import importlib.util
from pathlib import Path
import sys
import pytest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import signoff as SO
import test_hold_gate_ring as HG

TAG = '# OT_NATIVE_PAD_INPUT fclk_in_t_i t_i[*] -265.0000 166.6000\n'


def test_native_marker_parser_and_signoff_preserve_exact_eye():
    native = SO.native_pad_inputs(TAG)
    assert native == [('fclk_in_t_i', 't_i[*]', -265., 166.6)]
    t = SO.session_tcl('ff', [], True, native_pad_inputs=native, hold_in_min_ports={'t_i': -90})
    assert 'in $so_native_in} continue' in t
    # Last per-port write must restore native min AND max after any seam overlay.
    assert t.index('set_input_delay -min -265 -clock [get_clocks {fclk_in_t_i}]') > t.index('set_input_delay -min -90')
    assert 'set_input_delay -max 166.6 -clock [get_clocks {fclk_in_t_i}]' in t
    assert SO.native_pad_inputs('') == []


@pytest.mark.parametrize('line', [TAG+TAG, '# OT_NATIVE_PAD_INPUT x', TAG.replace('-265.0000', 'NaN'), TAG.replace('-265.0000', '1000'), TAG.replace('t_i[*]', 't_i;evil'), TAG.replace('fclk_in_t_i', 'x;evil')])
def test_native_marker_rejects_bad_contract(line):
    with pytest.raises(ValueError): SO.native_pad_inputs(line)


def test_hold_gate_keeps_native_delays(tmp_path):
    # The source gate uses OpenSTA get_clocks/get_ports -quiet. Existing ring harness models selectors.
    stubs = HG.STUBS.replace('proc get_clocks {x} {return $x}', 'proc get_clocks {args} {return [lindex $args end]}').replace('proc get_ports {x} {', 'proc get_ports {args} { set x [lindex $args end];')
    (tmp_path/'hold_gate.tcl').write_text(stubs + (HERE/'hold_gate.tcl').read_text())
    (tmp_path/'constraint.sdc').write_text(TAG)
    import subprocess
    r = subprocess.run(['tclsh', str(tmp_path/'hold_gate.tcl')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert 'SID -min -40 -clock vclk {a b cland_dn_ready_t_i}' in r.stdout
    assert 'SID -min -265.0000 -clock fclk_in_t_i {{t_i[0]} {t_i[1]}}' in r.stdout
    assert 'SID -max 166.6000 -clock fclk_in_t_i {{t_i[0]} {t_i[1]}}' in r.stdout
