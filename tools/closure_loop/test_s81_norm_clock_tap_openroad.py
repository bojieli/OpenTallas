"""Actual OpenDB: local tap keeps data, register count, polarity and root intact."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("cts", [True, False])
def test_local_leaf_tap(tmp_path, cts):
    if not shutil.which('openroad'):
        pytest.skip('OpenROAD required')
    definition='''VERSION 5.8 ;
DIVIDERCHAR "/" ; BUSBITCHARS "[]" ; DESIGN test ;
UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 200000 20000 ) ;
COMPONENTS 5 ;
- target DFF_TEST + PLACED ( 20000 5000 ) N ;
- neighbor DFF_TEST + PLACED ( 22000 6000 ) N ;
- clkbuf_leaf_far BUF_TEST + PLACED ( 150000 5000 ) N ;
- clkbuf_leaf_near BUF_TEST + PLACED ( 21000 5000 ) N ;
- clkbuf_leaf_alien BUF_TEST + PLACED ( 20000 5000 ) N ;
END COMPONENTS
PINS 4 ;
- clk + NET clk + DIRECTION INPUT + USE CLOCK + LAYER M1 ( 0 -20 ) ( 20 20 ) + FIXED ( 0 5000 ) N ;
- other + NET other + DIRECTION INPUT + USE CLOCK + LAYER M1 ( 0 -20 ) ( 20 20 ) + FIXED ( 0 10000 ) N ;
- data + NET data + DIRECTION INPUT + USE SIGNAL + LAYER M1 ( 0 -20 ) ( 20 20 ) + FIXED ( 0 3000 ) N ;
- ul_out[15] + NET out + DIRECTION OUTPUT + USE SIGNAL + LAYER M1 ( -20 -20 ) ( 0 20 ) + FIXED ( 200000 5000 ) N ;
END PINS
NETS 7 ;
- clk ( PIN clk ) ( clkbuf_leaf_far A ) ( clkbuf_leaf_near A ) + USE CLOCK ;
- other ( PIN other ) ( clkbuf_leaf_alien A ) + USE CLOCK ;
- far ( clkbuf_leaf_far Y ) ( target CLK ) + USE CLOCK ;
- near ( clkbuf_leaf_near Y ) ( neighbor CLK ) + USE CLOCK ;
- alien ( clkbuf_leaf_alien Y ) + USE CLOCK ;
- data ( PIN data ) ( target D ) ( neighbor D ) ;
- out ( target Q ) ( PIN ul_out[15] ) ;
END NETS
END DESIGN
'''
    (tmp_path/'test.def').write_text(definition)
    script=f'''read_lef {ROOT/'tools/closure_loop/testdata/io_flop_at_pins/test.lef'}
read_def {tmp_path/'test.def'}
set b [ord::get_db_block]
set ::cts_args {{}}
proc ::ot_ref_cts_boundary_orig {{args}} {{}}
source {ROOT/'physical/ref_tile/s81hc_ctfxnt_ref/local_clock_tap.tcl'}
source {ROOT/'physical/ref_tile/s81hc_ctfxnt_ref/local_clock_tap.tcl'}
if {{[[[$b findInst target] findITerm CLK] getNet] ne [$b findNet near]}} {{ error "target not locally tapped" }}
foreach name {{target neighbor}} {{
 if {{[[[$b findInst $name] findITerm D] getNet] ne [$b findNet data]}} {{ error "data changed" }}
}}
if {{[llength [$b getInsts]] != 5}} {{ error "state/buffer count changed" }}
if {{[ot_nt_clock_root [[[$b findInst target] findITerm CLK] getNet]] ne {{clk}}}} {{ error "clock root changed" }}
puts "NORM_CLOCK_FIXTURE_PASS"
exit
'''
    if not cts:
        script = script[:script.index('set ::cts_args')] + f'''set rc [catch {{source {ROOT/'physical/ref_tile/s81hc_ctfxnt_ref/local_clock_tap.tcl'}}} msg]
if {{!$rc || ![string match *outside* $msg] && ![string match *rerun* $msg]}} {{ error "missing replay guard: $msg" }}
if {{[[[$b findInst target] findITerm CLK] getNet] ne [$b findNet far]}} {{ error "replay mutated clock topology" }}
puts "NORM_CLOCK_REPLAY_GUARD_PASS"
exit
'''
    else:
        needle = f"source {ROOT/'physical/ref_tile/s81hc_ctfxnt_ref/local_clock_tap.tcl'}"
        first = script.index(needle) + len(needle)
        script = script[:first] + '\nrename ::ot_ref_cts_boundary_orig {}\nunset ::cts_args' + script[first:]
    (tmp_path/'cts.tcl').write_text(script)
    result=subprocess.run(['openroad','-no_init','-exit',str(tmp_path/'cts.tcl')],capture_output=True,text=True,check=True)
    assert ('NORM_CLOCK_FIXTURE_PASS' if cts else 'NORM_CLOCK_REPLAY_GUARD_PASS') in result.stdout, result.stdout
    assert result.stdout.count('NORM_CLOCK_TAP target/CLK:') == int(cts), result.stdout
