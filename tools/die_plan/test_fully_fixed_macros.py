"""Explicit fully fixed stage checks exact inventory; native stage order remains."""
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import fully_fixed_macros as F
import gen_phys as G
import schema as S

HERE=Path(__file__).resolve().parent


def declared(tmp_path,enabled=True):
    lef=tmp_path/'m.lef';lef.write_text('MACRO phy\n SIZE 777.6 BY 777.6 ;\nEND phy\n')
    t=dict(outline_um=[777.6,1641.6],fully_fixed_macros=enabled,kit_core_margins_um=[0,0,0,4.32],
           contents=[dict(inst='u_bound.u_io_ucie',module='phy',lef=str(lef),outline_um=[777.6,777.6])])
    macros=[('u_bound.u_io_ucie','phy',str(lef),'phy_tt.lib',0,0,'R0')]
    return t,macros


def test_absent_false_produce_no_files_or_config_changes(tmp_path):
    for t in ({},dict(fully_fixed_macros=False)):
        assert F.install(t,tmp_path,[],[],tmp_path)==[]
    assert not list(tmp_path.iterdir())
    with pytest.raises(ValueError):F.install(dict(fully_fixed_macros=True),tmp_path,[],[],tmp_path)


def test_generator_stages_standard_pre_hook_without_touching_placement_deck(tmp_path):
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
    t=raw['partition_types']['src']
    (tmp_path/'m.lef').write_text('MACRO phy\n SIZE 8.64 BY 8.64 ;\nEND phy\n')
    (tmp_path/'m_tt.lib').write_text('library(phy) {}\n')
    (tmp_path/'m_ff.lib').write_text('library(phy_ff) {}\n')
    t.setdefault('contents',[]).append(dict(inst='u_phy',module='phy',status='planned',lef='m.lef',lib='m_tt.lib',
                                             origin_um=[17.28,25.92],outline_um=[8.64,8.64],physical_inst='u_bound.u_phy',physical_master='phy'))
    normal=G.write_type_kit(S.Plan(raw),'src',tmp_path/'normal',[],root=tmp_path)
    t['fully_fixed_macros']=True
    fixed=G.write_type_kit(S.Plan(raw),'src',tmp_path/'fixed',[],root=tmp_path)
    assert (normal/'macro_place.tcl').read_bytes()==(fixed/'macro_place.tcl').read_bytes()
    a=(normal/'config.mk').read_text();b=(fixed/'config.mk').read_text()
    assert b==a.replace('export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n',
                       'export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\nexport PRE_MACRO_PLACE_TCL = /work/fully_fixed_macros.tcl\n')
    assert json.load(open(fixed/'fully_fixed_macros.json'))['macros'][0]['master']=='phy'
    assert json.load(open(fixed/'fully_fixed_macros.json'))['macros'][0]['instance']=='u_bound.u_phy'
    t['contents'][-1]['outline_um']=[8.7,8.64]
    with pytest.raises(ValueError,match='parent-plan outline'):
        G.write_type_kit(S.Plan(raw),'src',tmp_path/'bad',[],root=tmp_path)


def execute(tmp_path,mutant=None):
    t,macros=declared(tmp_path)
    F.install(t,tmp_path,macros,G.kit_core_area(t),tmp_path)
    hook=tmp_path/'fully_fixed_macros.tcl'
    if mutant=='overlap':
        hook.write_text(hook.read_text().replace('proc ot_fixed_macro_validate {} {',
            'dict set ::ot_fixed_macro_expected extra {phy 0 0 777.6 777.6 R0}\nproc ot_fixed_macro_validate {} {'))
    if mutant=='outside':
        hook.write_text(hook.read_text().replace('{phy 0 0 777.6 777.6 R0}','{phy 0.054 0 777.6 777.6 R0}'))
    setup=r'''
set ::events {}
proc rtl_macro_placer {args} {error NATIVE_OPTIMIZER_MUST_NOT_RUN}
proc bbox {m args} {dict get {xMin @X@ yMin 0 xMax @XMAX@ yMax 777600} $m}
proc core {m args} {dict get {xMin 0 yMin 0 xMax @COREX@ yMax 1637280} $m}
proc master {m args} {dict get {isBlock 1 getName @MASTER@ getWidth 777600 getHeight 777600} $m}
proc inst {m args} {dict get {getName u_bound.u_io_ucie getMaster master getPlacementStatus @STATUS@ getOrient @ORIENT@ getBBox bbox} $m}
proc extra {m args} {dict get {getName extra getMaster master getPlacementStatus LOCKED getOrient R0 getBBox bbox} $m}
proc blk {m args} {dict get {getDbUnitsPerMicron 1000 getInsts {@INSTS@} getCoreArea core} $m}
namespace eval ord {proc get_db_block {} {return blk}}
proc place_macro {args} {lappend ::events manual_placement}
proc erase_non_stage_variables {args} {}
proc load_design {args} {}
set ::env(SCRIPTS_DIR) /native/scripts
set ::env(RESULTS_DIR) /work/run/results
set ::env(MACRO_PLACEMENT_TCL) /work/macro_place.tcl
proc source_step_tcl {phase stage} {
 lappend ::events $phase
 if {$phase eq "PRE"} {real_source {@HOOK@}}
}
proc report_design_area {} {lappend ::events report_area}
proc orfs_write_db {args} {lappend ::events write_db}
proc write_macro_placement {args} {lappend ::events write_placement}
rename source real_source
proc source {path} {
 if {$path eq "/native/scripts/load.tcl"} {return}
 if {$path eq "/native/scripts/macro_place_util.tcl"} {
  # Native util sources the manual deck BEFORE unconditional rtl_macro_placer.
  place_macro -macro_name u_bound.u_io_ucie -location {0 0} -orientation R0 -exact
  rtl_macro_placer -halo_width .05 -halo_height .05
  return
 }
 error "unexpected stage source $path"
}
'''
    vals=dict(X=0,XMAX=777600,COREX=777600,MASTER='phy',STATUS='LOCKED',ORIENT='R0',INSTS='inst')
    if mutant in ('moved','outside'):vals.update(X=54,XMAX=777654)
    if mutant in ('extra','overlap'):vals['INSTS']='inst extra'
    if mutant=='missing':vals['INSTS']=''
    if mutant=='free':vals['STATUS']='PLACED'
    if mutant=='master':vals['MASTER']='other'
    if mutant=='orientation':vals['ORIENT']='MX'
    if mutant=='core':vals['COREX']=777550
    for k,v in vals.items():setup=setup.replace('@'+k+'@',str(v))
    setup=setup.replace('@HOOK@',str(tmp_path/'fully_fixed_macros.tcl'))
    # Pinned ORFS stage hashes inspected on the trial image:
    # macro_place.tcl f6cca8e16a76e1d6f72340b4b341e6fb6bf62fe2405f302afc7a97a0eb337262
    # macro_place_util.tcl 6e713fe75ac9937ef983cbbebe2c685b53354a8f9b9c7bdf62d0bf31abc5d4ee
    # Exact stage body; util fixture preserves manual-deck-before-optimizer ordering.
    stage='''source $::env(SCRIPTS_DIR)/load.tcl
erase_non_stage_variables floorplan
load_design 2_1_floorplan.odb 2_1_floorplan.sdc
source_step_tcl PRE MACRO_PLACE
source $::env(SCRIPTS_DIR)/macro_place_util.tcl
source_step_tcl POST MACRO_PLACE
report_design_area
orfs_write_db $::env(RESULTS_DIR)/2_2_floorplan_macro.odb
write_macro_placement $::env(RESULTS_DIR)/2_2_floorplan_macro.tcl
'''
    script=tmp_path/'stage.tcl';script.write_text(setup+'\n'+stage+'puts "ORDER $::events"\n')
    return subprocess.run(['tclsh',str(script)],text=True,capture_output=True)


@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh unavailable')
def test_fixed_macro_pass_preserves_native_stage_order(tmp_path):
    r=execute(tmp_path)
    assert r.returncode==0,r.stderr
    assert 'OT_FIXED_MACROS PASS 1' in r.stdout
    assert 'ORDER PRE manual_placement POST report_area write_db write_placement' in r.stdout


@pytest.mark.parametrize('mutant',['moved','extra','missing','free','master','orientation','core','outside','overlap'])
@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh unavailable')
def test_fixed_macro_bad_inventory_or_geometry_never_writes_output(tmp_path,mutant):
    r=execute(tmp_path,mutant)
    assert r.returncode!=0 and 'OT_FIXED_MACROS' in r.stderr,(r.stdout,r.stderr)
    assert 'write_db' not in r.stdout
