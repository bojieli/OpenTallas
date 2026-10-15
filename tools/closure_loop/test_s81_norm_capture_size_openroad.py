"""OpenDB fixture: ctfx_nt crossing-driver sizing (rule-based, every fd_in cone) preserves state and connections."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT = Path(__file__).resolve().parents[2]


def _lef(tmp_path):
    lef = (ROOT / 'tools/closure_loop/testdata/io_flop_at_pins/test.lef').read_text()
    buf = lef[lef.index('MACRO BUF_TEST'):lef.index('END LIBRARY')]
    extra = ''.join(buf.replace('BUF_TEST', m) for m in ('BUFx2_ASAP7_75t_R', 'BUFx4f_ASAP7_75t_R', 'HB1xp67_ASAP7_75t_R'))
    (tmp_path / 'cells.lef').write_text(lef.replace('END LIBRARY', extra + 'END LIBRARY'))


@pytest.mark.parametrize('cts', [True, False])
def test_crossing_driver_rule(tmp_path, cts):
    if not shutil.which('openroad'):
        pytest.skip('OpenROAD required')
    _lef(tmp_path)
    s = f'read_lef {tmp_path / "cells.lef"}\n'
    s += 'odb::dbBlock_create [odb::dbChip_create [ord::get_db]] top\nset b [ord::get_db_block]\n'
    s += 'proc mk {m n x} { set i [odb::dbInst_create $::b [[ord::get_db] findMaster $m] $n]; $i setLocation [expr {$x*1000}] 0; $i setPlacementStatus PLACED; return $i }\n'
    # bit 0: pin -> HB -> hold_a (BUFx2) -> {capture at 10 um, clone at 90 um}: crossing wire, must be sized
    # bit 1: pin -> HB -> hold_b (BUFx2) -> {capture at 10 um, clone at 15 um}: short, must stay BUFx2
    for bit, far in ((0, 90), (1, 15)):
        s += f'''set p [odb::dbNet_create $b fd_in_{bit}]
set bt [odb::dbBTerm_create $p {{fd_in[{bit}]}}]; $bt setIoType INPUT
set hb [mk HB1xp67_ASAP7_75t_R ot_inhold_{bit} 5]; [$hb findITerm A] connect $p
set n1 [odb::dbNet_create $b m_{bit}]; [$hb findITerm Y] connect $n1
set h [mk BUFx2_ASAP7_75t_R hold_{bit} 8]; [$h findITerm A] connect $n1
set d [odb::dbNet_create $b d_{bit}]; [$h findITerm Y] connect $d
[[mk DFF_TEST cap_{bit} 10] findITerm D] connect $d
[[mk DFF_TEST clone_{bit} {far}] findITerm D] connect $d
'''
    s += '''set placements 0
proc detailed_placement {} { incr ::placements }
proc check_placement {args} {}
proc estimate_parasitics {args} {}
proc set_dont_touch {args} {}
rename get_cells real_get_cells
proc get_cells {args} { return $args }
'''
    if cts:
        s += 'set ::cts_args {}\nproc ::ot_ref_cts_boundary_orig {args} {}\n'
    hook = ROOT / 'physical/ref_tile/s81hc_ctfxnt_ref/capture_driver_size.tcl'
    s += f'source {hook}\n'
    want0 = 'BUFx4f_ASAP7_75t_R' if cts else 'BUFx2_ASAP7_75t_R'
    s += f'if {{[[[$b findInst hold_0] getMaster] getName] ne "{want0}"}} {{ error "crossing driver size" }}\n'
    s += 'if {[[[$b findInst hold_1] getMaster] getName] ne "BUFx2_ASAP7_75t_R"} { error "short net resized" }\n'
    s += f'if {{$placements != {1 if cts else 0}}} {{ error "legal placement count $placements" }}\n'
    s += 'if {[llength [$b getInsts]] != 8 || [llength [$b getNets]] != 6} { error "topology changed" }\n'
    s += 'foreach k {0 1} { foreach f [list cap_$k clone_$k] { if {[[[$b findInst $f] findITerm D] getNet] ne [$b findNet d_$k]} { error "data changed" } } }\n'
    s += 'puts "NORM_CAPTURE_SIZE_FIXTURE_PASS"\nexit\n'
    p = tmp_path / 'test.tcl'
    p.write_text(s)
    r = subprocess.run(['openroad', '-exit', '-no_init', str(p)], capture_output=True, text=True)
    assert r.returncode == 0 and 'NORM_CAPTURE_SIZE_FIXTURE_PASS' in r.stdout, r.stdout + r.stderr
