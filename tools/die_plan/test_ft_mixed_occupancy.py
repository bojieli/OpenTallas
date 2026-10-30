"""Pre-reserve explicit FT targets independently of BTerm placement order."""
from pathlib import Path
import subprocess
import pytest


def run(explicit='', full='', before=False, y=0):
    src=Path(__file__).with_name('face_flops.tcl').read_text()
    body='set ff_gocc {}'+src.split('set ff_gocc {}',1)[1].split('set ff_st 0',1)[0]
    script='''set ff_x0 0; set ff_y0 0; set ff_x1 100; set ff_y1 30
set ff_rh 10; set ff_sw 1; set ff_cpitch 10; set ff_dbu 1
set ff_orient [dict create 0 R0 10 R0 20 R0]
set ff_bit_sites [dict create %s]
set ff_bit_site_cells [dict create slot {5 10}]
set ff_full_targets {%s}
proc master {cmd} {if {$cmd eq "getWidth"} {return 5}; return 10}
proc cell {cmd args} {if {$cmd eq "getMaster"} {return master}; if {$cmd eq "getPlacementStatus"} {return UNPLACED}; if {$cmd eq "getName"} {return cell}}
'''%(explicit,full)+body
    if before:script+='ff_put_stage cell slot 1 {slot_i[0]} {10 0}\n'
    script+='puts [ff_put_near cell 10 %d]\n'%y
    if explicit and not before:script+='ff_put_stage cell slot 1 {slot_i[0]} {10 0}\n'
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True)
    assert not result.stderr,result.stderr
    return tuple(map(int,result.stdout.splitlines()[0].split()))


def test_default_without_explicit_targets_stays_exact():
    assert run()==(10,0)


@pytest.mark.parametrize('before',[False,True])
def test_explicit_target_is_reserved_before_or_after_implicit_call(before):
    assert run('slot,1,0 {10 0}',before=before)==(0,0)


def test_full_stage_targets_are_also_reserved():
    assert run(full='{slot 0 0 actual master 10 0 5 10}')==(0,0)


def test_edge_touching_neighbor_remains_legal():
    # Explicit body ends exactly where the implicit body starts.
    assert run('slot,1,0 {5 0}')==(10,0)
