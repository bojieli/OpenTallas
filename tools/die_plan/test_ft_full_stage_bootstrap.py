"""Fresh native DPL process receives only pure FT validation support."""
import json
import subprocess
from pathlib import Path
import pytest
from ft_full_stage import install, validation_bootstrap

HERE = Path(__file__).parent

def test_bootstrap_uses_exact_pure_helpers_and_fails_closed():
    face = (HERE/'face_flops.tcl').read_text()
    boot = validation_bootstrap(face)
    for word in ('setLocation', 'setPlacementStatus', 'ff_clone_for', 'ff_put_near', 'ot_face_flops.txt'):
        assert word not in boot
    for name in ('ff_from_in', 'ff_from_out', 'ff_lands_ring', 'ff_landed_stations'):
        assert f'proc {name} ' in boot
    with pytest.raises(ValueError, match='ff_landed_stations'):
        validation_bootstrap(face.replace('proc ff_landed_stations ', 'proc renamed '))


def test_bootstrap_refuses_mutating_initialization_from_a_patched_kit_hook():
    face = (HERE/'face_flops.tcl').read_text()
    init = 'set ff_blk [ord::get_db_block]'
    for patch in ('set ff_log [open $::env(RESULTS_DIR)/x.txt w]', '[$ff_blk findInst a] setLocation 0 0',
                  'set fa [open /work/y a]'):
        with pytest.raises(ValueError, match='mutating code'):
            validation_bootstrap(face.replace(init, init + '\n' + patch, 1))
    # The kit's read-only ft_stations.txt reader stays allowed.
    assert 'open /work/ft_stations.txt r' in validation_bootstrap(face)

def test_active_install_bootstraps_fresh_orfs_proc_without_normal_placement(tmp_path):
    doc = dict(schema='opentallas.ft_full_stage.v1', module='m', outline_um=[1000,100],
               slots={'ft0':dict(stations=4,width=0,in_face='W',out_face='E',targets=[
                   dict(stage=j,bit=0,name=f'q{j}',master='DFF',xy=[j*330,10],size=[1.08,.27]) for j in range(4)])})
    t = dict(module='m',outline_um=[1000,100],ft_slots=[dict(name='ft0',stations=4,width=0,in_face='W',out_face='E')],ft_full_stage_placement_file='map.json')
    (tmp_path/'map.json').write_text(json.dumps(doc))
    (tmp_path/'face_flops.tcl').write_text((HERE/'face_flops.tcl').read_text())
    (tmp_path/'face_flops_release.tcl').write_text('# original release\n')
    install(t,tmp_path/'plan.json',tmp_path)
    release = (tmp_path/'face_flops_release.tcl').read_text()
    assert release.index('ft_full_stage_bootstrap.tcl') < release.index('source /work/ft_full_stage.tcl')
    assert 'source /work/face_flops.tcl' not in release
    (tmp_path/'ft_stations.txt').write_text('ft0 4 W E\n')
    boot = (tmp_path/'ft_full_stage_bootstrap.tcl').read_text().replace('/work/',str(tmp_path)+'/')
    (tmp_path/'boot.tcl').write_text(boot)
    script = r'''
namespace eval ord {}
proc ord::get_db_block {} {return block}
proc ord::get_db_tech {} {return tech}
proc block {method} {if {$method eq "getCoreArea"} {return box};if {$method eq "getRows"} {return row};error "mutating normal hook unexpectedly ran"}
proc tech {method} {return 1000}
proc box {method} {switch $method {xMin - yMin {return 0} xMax {return 1000000} yMax {return 100000}}}
proc row {method} {switch $method {getSite {return site} getOrigin {return {0 0}} getOrient {return R0}}}
proc site {method} {if {$method eq "getWidth"} {return 54};return 270}
proc orfs_source_hook {} {source BOOT}
orfs_source_hook
if {$ff_dbu!=1000 || $ff_sw!=54 || $ff_rh!=270 || [llength $ff_full_targets]!=4 || [dict get $ff_full_slots ft0]!=4} {error "fresh global/data bootstrap missing"}
if {[ff_slot_of ft0_i _i] ne "ft0"} {error "native slot lookup missing"}
if {[info exists ff_out] || [info commands ff_clone_for] ne ""} {error "normal placement/cloning leaked"}
puts FRESH_PROCESS_BOOTSTRAP_PASS
'''.replace('source BOOT','source {'+str(tmp_path/'boot.tcl')+'}')
    p = subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and not p.stderr,p.stdout+p.stderr
    assert 'FRESH_PROCESS_BOOTSTRAP_PASS' in p.stdout
