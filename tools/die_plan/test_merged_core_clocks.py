import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import cores as C
import gen_phys as G
import merged_core_clocks as M


def fixture(tmp_path):
    names = ['clk_pair[0]', 'clk_pair[1]']
    pins = [dict(name=n, layer='M5', x=i+.5, y=1.5) for i, n in enumerate(names)]
    (tmp_path/'pins.json').write_text(json.dumps(pins))
    lef = 'MACRO hcol\n'
    lib = 'library (L) { cell (hcol) {'
    for i, n in enumerate(names):
        lef += f' PIN {n}\n DIRECTION INPUT ;\n USE CLOCK ;\n PORT\n LAYER M5 ;\n RECT {i} 1 {i+1} 2 ;\n END\n END {n}\n'
        lib += f'pin ("{n}") {{ direction : input;\n clock : true; }}'
    (tmp_path/'core.lef').write_text(lef+'END hcol\n')
    (tmp_path/'core.lib').write_text(lib+'}}')
    tap = dict(name='u_h.clk_pair', kind='core', xy=[1, 1.5], insertion_ps=250,
               merged_clock_ports=names)
    core = dict(inst='u_h', module='hcol', pins_file='pins.json',
                lef=str(tmp_path/'core.lef'), lib=str(tmp_path/'core.lib'))
    t = dict(clock=dict(core_taps='early', taps=[tap]), hard_cores=[core])
    return SimpleNamespace(types={'p':t}, path=tmp_path/'plan.json', clock=dict(insertion_ps=250)), tap


def test_exact_two_bit_same_source_and_latency(tmp_path):
    p, tap = fixture(tmp_path)
    assert M.pins(p, 'p', tap, 'u_h') == tap['merged_clock_ports']
    rows = G.core_tap_rows(p, 'p')
    assert [(r[0], r[1], r[2]) for r in rows] == [('clk_c0','u_h','clk_pair[0]'),('clk_c0','u_h','clk_pair[1]')]
    assert {C.core_tap_of(p.types['p'],'u_h',pin) for pin in tap['merged_clock_ports']} == {'clk_c0'}


@pytest.mark.parametrize('mutant', ['missing_bit', 'fake_geometry', 'lib_missing_bit'])
def test_missing_or_fabricated_bit_rejected(tmp_path, mutant):
    p, tap = fixture(tmp_path)
    if mutant == 'lib_missing_bit':
        f = tmp_path/'core.lib'; f.write_text(f.read_text().replace('clock : true;', 'clock : false;', 1))
    else:
        f = tmp_path/'pins.json'; rows=json.loads(f.read_text())
        if mutant == 'missing_bit': rows.pop()
        else: rows[0]['x'] += 1
        f.write_text(json.dumps(rows))
    with pytest.raises(ValueError): G.core_tap_rows(p, 'p')


def test_tcl_materializes_both_bits_and_missing_bit_fails(tmp_path):
    import shutil
    import subprocess
    if not shutil.which('tclsh'): pytest.skip('tclsh unavailable')
    text=(Path(__file__).with_name('clock_taps.tcl')).read_text()
    block=text[text.index('if {[info exists ::env(OT_CORE_TAPS)]'):text.index('if {[llength $ct_taps] < 2}')]
    rows=tmp_path/'taps.txt'
    rows.write_text('clk_c0 u_h clk_pair[0] 0 250 exact\nclk_c0 u_h clk_pair[1] 0 250 exact\n')
    mock=r'''
set ct_blk blk
set ct_port clk
set missing 0
array set nets {it0 root it1 root}
proc blk {method arg} { if {$method eq "findBTerm"} {return [expr {$arg eq "clk" ? "btroot" : "bttap"}]} ; return inst }
proc btroot {method args} { return root }
proc bttap {method args} { return tap }
proc inst {method args} {
 global missing
 if {$method eq "findITerm"} { if {[lindex $args 0] eq {clk_pair[1]}} {return [expr {$missing ? "NULL" : "it1"}]} ; return it0 }
 return {it0 it1}
}
proc root {args} {}
proc tap {args} {}
proc it {name method args} {
 global nets
 switch $method {
  getNet {return $nets($name)}
  isInputSignal {return 1}
  getMTerm {return [expr {$name eq "it0" ? "mt0" : "mt1"}]}
  disconnect {set nets($name) NULL}
  connect {set nets($name) [lindex $args 0]}
 }
}
interp alias {} it0 {} it it0
interp alias {} it1 {} it it1
proc mt0 {method} {return {clk_pair[0]}}
proc mt1 {method} {return {clk_pair[1]}}
proc get_pins {args} { return [lindex [lindex $args end] 0] }
proc get_cells {args} { return cell }
proc get_lib_cells {args} { return libcell }
proc get_lib_pins {args} { return {lp0 lp1} }
proc get_property {lp prop} { if {$prop eq "is_clock"} {return 1}; return [expr {$lp eq "lp0" ? "clk_pair\[0\]" : "clk_pair\[1\]"}] }
'''
    for missing in (False, True):
        script=mock+f'\nset ::env(OT_CORE_TAPS) {{{rows}}}\nset missing {int(missing)}\n'
        script+='if {[catch {\n'+block+'\n} why]} {puts $why; exit 7}\n'
        script+='if {$nets(it0) ne "tap" || $nets(it1) ne "tap"} {exit 8}\nputs BOTH_ACTUAL_BITS_CONNECTED\n'
        result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
        assert result.returncode == (7 if missing else 0), result.stdout+result.stderr
        assert ('missing exact input' if missing else 'BOTH_ACTUAL_BITS_CONNECTED') in result.stdout
