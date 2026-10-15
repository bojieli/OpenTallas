"""OpenDB fixture: measured dual-D driver sizing preserves state and connections."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('cts',[True,False])
def test_measured_capture_driver(tmp_path,cts):
    if not shutil.which('openroad'):pytest.skip('OpenROAD required')
    lef=(ROOT/'tools/closure_loop/testdata/io_flop_at_pins/test.lef').read_text()
    buf=lef[lef.index('MACRO BUF_TEST'):lef.index('END LIBRARY')]
    lef=lef.replace('END LIBRARY',buf.replace('BUF_TEST','BUFx2_ASAP7_75t_R')+buf.replace('BUF_TEST','BUFx3_ASAP7_75t_R')+'END LIBRARY')
    (tmp_path/'cells.lef').write_text(lef)
    bits=[1004,1018,857,855,853,840,838]
    script=f'read_lef {tmp_path/"cells.lef"}\n'
    script+='odb::dbBlock_create [odb::dbChip_create [ord::get_db]] top\nset b [ord::get_db_block]\n'
    for bit in bits:
        script+=f'''set h [odb::dbInst_create $b [[ord::get_db] findMaster BUFx2_ASAP7_75t_R] hold_{bit}]
set n [odb::dbNet_create $b d_{bit}]
[$h findITerm Y] connect $n
set f [odb::dbInst_create $b [[ord::get_db] findMaster DFF_TEST] {{fdx[{bit}]$_DFF_P_}}]
[$f findITerm D] connect $n
set f [odb::dbInst_create $b [[ord::get_db] findMaster DFF_TEST] clone_{bit}]
[$f findITerm D] connect $n
'''
    script+='''set placements 0
proc detailed_placement {} { incr ::placements }
proc check_placement {args} {}
proc estimate_parasitics {args} {}
proc set_dont_touch {args} {}
rename get_cells real_get_cells
proc get_cells {args} { return $args }
'''
    if cts:script+='set ::cts_args {}\nproc ::ot_ref_cts_boundary_orig {args} {}\n'
    hook=ROOT/'physical/ref_tile/s81hc_ctfxnt_ref/capture_driver_size.tcl'
    script+=f'set rc [catch {{source {hook}}} msg]\n'
    if cts:
        script+='if {$rc} { error $msg }\n'
        script+='unset ::cts_args\nrename ::ot_ref_cts_boundary_orig {}\n'
        script+=f'source {hook}\nif {{$placements != 1}} {{ error "legal placement/idempotence" }}\n'
    else:script+='if {!$rc || ![string match *outside* $msg]} { error "missing replay guard: $msg" }\n'
    script+=f'if {{[llength [$b getInsts]] != 21 || [llength [$b getNets]] != 7}} {{ error "state/topology changed" }}\n'
    for bit in bits:
        target='BUFx3_ASAP7_75t_R' if cts else 'BUFx2_ASAP7_75t_R'
        script+=f'''if {{[[[$b findInst hold_{bit}] getMaster] getName] ne "{target}"}} {{ error "wrong size" }}
if {{[[[$b findInst {{fdx[{bit}]$_DFF_P_}}] findITerm D] getNet] ne [$b findNet d_{bit}]}} {{ error "data changed" }}
if {{[[[$b findInst clone_{bit}] findITerm D] getNet] ne [$b findNet d_{bit}]}} {{ error "clone changed" }}
'''
    script+='puts "NORM_CAPTURE_SIZE_FIXTURE_PASS"\nexit\n'
    p=tmp_path/'test.tcl';p.write_text(script)
    r=subprocess.run(['openroad','-exit','-no_init',str(p)],capture_output=True,text=True)
    assert r.returncode==0 and 'NORM_CAPTURE_SIZE_FIXTURE_PASS' in r.stdout,r.stdout+r.stderr
