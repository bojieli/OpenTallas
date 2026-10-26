import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import core_clock_groups as CG
import gen_phys as GP
import gen_rtl as GR
import schema as S
from test_cp2 import cp2_pair,HERE


def setup_plan(tmp_path):
    raw,p,leaves,_=cp2_pair(str(tmp_path))
    ck=p['partition_types']['src']['clock'];base=ck['taps'][0]
    ck['taps'].append(dict(base,name='u_leaf.u_core.ck2',insertion_ps=100))
    ck['core_groups']=[dict(name='selected',port='clk_selected',xy=[30,30],members=[dict(inst='u_leaf.u_core',pin='clk',tap='u_leaf.u_core.clk')],insertion_ps=550,insertion_ff_ps=430,basis='parent_budget',source='explicit tiny first-route budget',network=dict(nodes=[dict(name='u_ccg0',parent='@root',cell='BUFx24_ASAP7_75t_R',ll_um=[20,20],orient='R0')],endpoints=[dict(inst='u_leaf.u_core',pin='clk',parent='u_ccg0')]))]
    return p,leaves


def test_endpoint_contract_consumers_agree_and_ordinary_stable(tmp_path):
    p,leaves=setup_plan(tmp_path);P=S.Plan(p)
    assert not S.validate(p),S.validate(p)
    taps=S.core_taps(P,'src');assert [x[0] for x in taps]==['clk_c1','clk_selected']
    assert GP.core_tap_rows(P,'src')==[('clk_c1','u_leaf.u_core','ck2',0,100),('clk_selected','u_leaf.u_core','clk',300,550)]
    sv=GR.wrapper(P,'src',{})
    assert sv.count('input  wire clk_selected')==1 and 'input  wire clk_c0' not in sv and 'input  wire clk_c1' in sv
    sdc=GP.sdc(P,'src',[])
    assert 'get_ports clk_selected' in sdc and 'get_ports clk_c0' not in sdc
    import die_clock
    endpoints=die_clock.plan_taps(P)
    assert any(x[1]=='clk_selected' and x[4]==300 for x in endpoints)
    assert not any(x[1]=='clk_c0' for x in endpoints if x[0]=='pa')
    assert die_clock.plan_tap_early(P)[('pa','clk_selected')]=={'TT':300,'FF':227.5}
    manifest=CG.network_manifest(P,'src');assert manifest['release_qualified'] is False
    assert 'ot_ccg::setup' in CG.tcl_text(manifest)


@pytest.mark.parametrize('mutation,match',[
 (lambda g:g['members'].append(copy.deepcopy(g['members'][0])),'duplicate'),
 (lambda g:g['members'][0].update(inst='missing'),'exact existing'),
 (lambda g:g['members'][0].update(tap='not_a_tap'),'does not match'),
 (lambda g:g.update(insertion_ff_ps=float('nan')),'positive TT/FF'),
 (lambda g:g.update(basis='signed_pin_mean'),'requires explicit parent_budget'),
 (lambda g:g.update(port='clk_c0'),'reserved'),
 (lambda g:g['network']['endpoints'].clear(),'membership differs'),
 (lambda g:g['network']['nodes'][0].update(parent='future_node'),'out-of-order'),
 (lambda g:g.pop('network'),'complete physical network'),
])
def test_fail_closed_membership_and_physical_network(tmp_path,mutation,match):
    p,_=setup_plan(tmp_path);mutation(p['partition_types']['src']['clock']['core_groups'][0])
    with pytest.raises(ValueError,match=match):CG.network_manifest(S.Plan(p),'src')


def test_no_optin_is_identical(tmp_path):
    _,p,_,_=cp2_pair(str(tmp_path));P=S.Plan(p)
    assert [x[0] for x in S.core_taps(P,'src')]==['clk_c0']
    assert CG.network_manifest(P,'src')['groups']==[]


def test_generated_kit_contains_manifest_and_runtime_after_cp2_rewire(tmp_path):
    p,leaves=setup_plan(tmp_path)
    leaf=tmp_path/'leaves.sv';leaf.write_text(leaves)
    for t in p['partition_types'].values():t['sources']=[str(leaf)]
    kits=GP.write_phys(p,tmp_path/'kits',str(HERE.parent.parent),proof=True)
    kit=next(k for k in kits if k.name=='src')
    assert json.loads((kit/'core_clock_groups.json').read_text())['groups'][0]['port']=='clk_selected'
    hook=(kit/'pre_cts.tcl').read_text()
    assert hook.index('source /work/clock_taps.tcl') < hook.index('source /work/core_clock_groups_apply.tcl')
    assert (kit/'core_clock_groups.tcl').is_file()
    assert 'clk_selected u_leaf.u_core clk 300 550' in (kit/'core_taps.txt').read_text()
    assert 'core_groups' not in (next(k for k in kits if k.name=='mid')/'pre_cts.tcl').read_text()


def test_runtime_is_optin_and_cts_excludes_group_inputs():
    import shutil,subprocess
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    runtime=Path(__file__).resolve().parents[2]/'physical/common_flow/core_clock_groups.tcl'
    body='''
proc loader {} {source RUNTIME}
loader
puts "OFF [info commands ::clock_tree_synthesis]"
namespace eval ord {proc get_db_block {} {return blk}}
rename ::ot_ccg::audit ::ot_ccg::audit_orig
proc ::ot_ccg::audit {b} {incr ::audits}
rename ::ot_ccg::bind_new_pg ::ot_ccg::bind_new_pg_orig
proc ::ot_ccg::bind_new_pg {b} {incr ::pgs}
set audits 0;set pgs 0;set repairs 0
proc estimate_parasitics {args} {}
namespace eval est {proc check_parasitics {} {}}
namespace eval sta {proc db_net_to_sta {n} {return $n}}
namespace eval rsz {
 proc check_max_wire_length {args} {return 100}
 proc repair_net_cmd {args} {incr ::repairs}
}
set ::ot_ccg::groups [dict create clk_selected groupnet]
proc ::ot_ccg::cts_orig {args} {set ::args $args;return ok}
proc all_clocks {} {return clk}
proc get_property {c prop} {return {clk clk_c1 clk_selected}}
proc get_full_name {n} {return $n}
proc blk {m n} {return $n}
proc clk {m} {return root}
proc clk_c1 {m} {return ordinary_cp2}
proc root {m} {return root}
proc ordinary_cp2 {m} {return ordinary_cp2}
puts "RETURN [::ot_ccg::cts -root_buf BUF -repair_clock_nets -clk_nets stale]"
puts "ARGS $args AUDITS $audits PG $pgs REPAIRS $repairs"
'''.replace('RUNTIME','{'+str(runtime)+'}')
    p=subprocess.run(['tclsh'],input=body,text=True,capture_output=True)
    assert not p.stderr,p.stderr
    assert 'OFF \n' in p.stdout
    assert 'ARGS -root_buf BUF -clk_nets {ordinary_cp2 root} AUDITS 2 PG 2 REPAIRS 2' in p.stdout


def test_hbm_first_buffer_guard_rejects_long_unbuffered_entry():
    import shutil,subprocess
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    runtime=Path(__file__).resolve().parents[2]/'physical/die_plan/hbm_arch_cores/hbm_clock_entry.tcl'
    body='''
proc loader {} {source RUNTIME}
loader
puts "OFF [info commands ::clock_tree_synthesis]"
set xi 19000
proc block {m args} {if {$m eq "findBTerm"} {return bt};return 1000}
proc bt {m} {if {$m eq "getNet"} {return net};return bp}
proc net {m} {return it}
proc it {m} {switch $m {isInputSignal {return 1} getInst {return inst} getBBox {return ip} getMTerm {return A}}}
proc inst {m} {if {$m eq "getMaster"} {return master};return first_buf}
proc master {m} {if {$m eq "getName"} {return BUFx24_ASAP7_75t_R};return 0}
proc bp {m} {switch $m {xMin - xMax {return 1000} yMin - yMax {return 2000}}}
proc ip {m} {switch $m {xMin - xMax {return $::xi} yMin - yMax {return 2000}}}
set ::ot_hbmentry::block block;set ::ot_hbmentry::port tile_clk
set ::ot_hbmentry::max_um 20;set ::ot_hbmentry::root_net net
puts "SHORT [catch {::ot_hbmentry::check} msg] $msg"
set xi 22000
puts "LONG [catch {::ot_hbmentry::check} msg] $msg"
'''.replace('RUNTIME','{'+str(runtime)+'}')
    p=subprocess.run(['tclsh'],input=body,text=True,capture_output=True)
    assert not p.stderr,p.stderr
    assert 'OFF \n' in p.stdout
    assert 'SHORT 0 18.0' in p.stdout
    assert 'LONG 1 OT_HBM_ENTRY unbuffered root segment 21.0 um exceeds 20 um' in p.stdout
