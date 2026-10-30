"""Actual native root connectivity overrides spelling, never counts/period rules."""
import copy
import json
from pathlib import Path

import pytest
import schema as S
import native_clock_domains as N
import master_plan as MP
import reset_tree as R
import taps

HERE=Path(__file__).resolve().parent


def witness(module,roots,counts,macros=(),sha='a'*64):
    pins=[]
    for net,n in counts.items():
        for i in range(n):pins.append(dict(inst=net+'_ff'+str(i),master='DFFHQNx1_ASAP7_75t_R',pin='CLK',net=net,status='NONE'))
    return dict(top_module=module,source_odb_sha256=sha,clock_root_ports=[dict(port=p,net=n,dir='INPUT') for p,n in roots],
                ff_count=len(pins),ff_clock_net_counts=counts,ff_clock_pins=pins,macro_clock_pins=list(macros))


@pytest.fixture
def vehicle(tmp_path):
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text());t=raw['partition_types']['src']
    t['outline_um']=[400.,300.]
    t['hard_cores']=[dict(inst='u_child',module='ip',origin_um=[17.28,25.92],outline_um=[8.64,8.64],
        pins=[dict(name='clk',layer='M5',xy=[4.32,4.32]),dict(name='rst_n',layer='M5',xy=[4.32,4.59])])]
    macro=dict(inst='u_child',master='ip',pin='clk',net='pma_rck[0]')
    parent=witness(t['module'],[('clk','clk'),('pma_rck[0]','pma_rck[0]'),('fclk_in_loop','fclk_in_loop')],
                   {'clk':3,'pma_rck[0]':2,'fclk_in_loop':1},[macro])
    child=witness('ip',[('clk','clk')],{'clk':2},sha='b'*64)
    (tmp_path/'parent.json').write_text(json.dumps(parent));(tmp_path/'child.json').write_text(json.dumps(child))
    spec=dict(schema='opentallas.native_clock_domains.v1',census_file='parent.json',source_odb_sha256='a'*64,
              core_root='clk',macro_pins=[dict(inst='u_child',module='ip',pin='clk',root='pma_rck')],
              children=[dict(inst='u_child',module='ip',pin='clk',root='pma_rck',census_file='child.json',source_odb_sha256='b'*64)])
    t.setdefault('clock',{})['native_domains']=spec
    P=S.Plan(raw,tmp_path/'plan.json')
    return P,parent,child,tmp_path


def test_separate_actual_parent_roots_and_child_internal_ff(vehicle):
    P,*_=vehicle;c=N.contract(P,'src')
    assert {r:v['parent_ff'] for r,v in c['roots'].items()}==dict(clk=3,pma_rck=2,fclk_in_loop=1)
    assert c['core_grid_parent_ff']==3 and c['child_internal_ff_excluded']==2
    assert N.macro_root(P,'src','u_child','ip','clk')=='pma_rck'
    assert 'PREP' in c['electrical_status'] and N.core_planning_sites(P,'src') is None


def test_master_entry_uses_exact_native_net_witness_not_pin_spelling(vehicle):
    P,*_=vehicle;h=P.types['src']['hard_cores'][0]
    tap=dict(name='u_child.clk',kind='landed',clock_domain='pma_rck',forwarded=True,xy=[21.6,30.24])
    r=MP.core_clock_entry_check(P,h,[tap],[4.32,4.32],tn='src')
    assert r['verdict']=='PASS' and r['native_net_root']=='pma_rck'
    assert MP.core_clock_entry_check(P,h,[dict(tap,clock_domain='clk')],[4.32,4.32],tn='src')['verdict']=='FAIL'
    assert MP.core_clock_entry_check(P,h,[dict(tap,forwarded=False)],[4.32,4.32],tn='src')['verdict']=='FAIL'
    # Defaults retain the old pin-name rule when no source witness is opted in.
    P.types['src']['clock'].pop('native_domains')
    assert MP.core_clock_entry_check(P,h,[tap],[4.32,4.32],tn='src')['verdict']=='FAIL'


def test_core_density_planning_excludes_other_roots_and_child_ff(vehicle):
    P,*_=vehicle;ck=P.types['src']['clock'];ck['sink_sites_um']=[[100,100,999]]
    with pytest.raises(ValueError,match='aggregate bins are unqualified'):taps.sink_sites(P,'src',control=False)
    ck['native_domains']['planned_sink_sites']={'clk':[[10,20,3]],'pma_rck':[[40,50,2]],'fclk_in_loop':[[60,70,1]]}
    assert taps.sink_sites(P,'src',control=False)==[(10.,20.,3.)]
    ck['native_domains']['planned_sink_sites']['clk'][0][2]=5
    with pytest.raises(ValueError,match='parent FF inventory'):taps.sink_sites(P,'src',control=False)


def test_reset_geometry_records_actual_child_root_without_reclocking_or_period(vehicle):
    P,*_=vehicle
    targets=R.core_reset_targets(P,'src')
    assert len(targets)==1 and targets[0]['native_clock_root']=='pma_rck'
    before={k:v for k,v in targets[0].items() if not k.startswith('native_clock_')}
    P.types['src']['clock'].pop('native_domains')
    assert R.core_reset_targets(P,'src')==[before]


@pytest.mark.parametrize('mutant',['module','master','pin','root_alias','missing_macro','duplicate_ff','count','unrooted_ff','child_top','child_count','source_sha','core_is_pma','child_double'])
def test_false_source_binding_and_bad_census_fail_closed(vehicle,mutant):
    P,parent,child,path=vehicle;s=P.types['src']['clock']['native_domains']
    if mutant=='module':parent['top_module']='other'
    if mutant=='master':s['macro_pins'][0]['module']='other'
    if mutant=='pin':s['macro_pins'][0]['pin']='ck'
    if mutant=='root_alias':s['macro_pins'][0]['root']='invented'
    if mutant=='missing_macro':s['macro_pins']=[]
    if mutant=='duplicate_ff':parent['ff_clock_pins'].append(parent['ff_clock_pins'][0])
    if mutant=='count':parent['ff_count']+=1
    if mutant=='unrooted_ff':parent['ff_clock_pins'][0]['net']='not_a_root'
    if mutant=='child_top':child['top_module']='other'
    if mutant=='child_count':child['ff_count']+=1
    if mutant=='source_sha':s['source_odb_sha256']='c'*64
    if mutant=='core_is_pma':s['core_root']='pma_rck'
    if mutant=='child_double':s['children']*=2
    (path/'parent.json').write_text(json.dumps(parent));(path/'child.json').write_text(json.dumps(child))
    with pytest.raises(ValueError):N.contract(P,'src')


def test_scalar_and_bit_zero_root_collision_is_rejected_before_map_merge(vehicle):
    P,parent,child,path=vehicle
    parent['clock_root_ports'].append(dict(port='pma_rck',net='other_actual_net',dir='INPUT'))
    (path/'parent.json').write_text(json.dumps(parent))
    with pytest.raises(ValueError,match='canonical root collision'):
        N.contract(P,'src')


def test_noncore_native_release_keeps_raw_target_but_no_core_cycle_credit(vehicle):
    P,*_=vehicle
    P.reset['release']='wavefront'
    targets=R.core_reset_targets(P,'src')
    W=R.wf_plan(P)
    part=next(name for name,row in W['parts'].items() if row['type']=='src')
    row=W['parts'][part]
    assert row['core_release']['u_child.rst_n'] is None
    native=row['native_release']['u_child.rst_n']
    assert native['status']=='PENDING' and native['native_clock_root']=='pma_rck'
    assert native['core_cycle_release'] is None and native['raw_pin_arrival_core_cycles']==row['release']
    assert native['internal_depth_native_cycles']==1
    assert W['types']['src']['core_resets'][0]['pin_um']==targets[0]['pin_um']
    assert W['types']['src']['core_resets'][0]['xy']==targets[0]['xy']
    assert W['release_qualification']['verdict']=='PENDING'
    errs,_,info=R.check(P)
    assert any('FULL native release qualification PENDING' in e for e in errs)
    assert info['release_qualification']['verdict']=='PENDING'


def test_full_smoke_refuses_pending_native_release_before_calendar_credit(tmp_path):
    import bind_smoke
    top=tmp_path/'rtl'/'parts'/'top.sv';top.parent.mkdir(parents=True)
    metadata=top.parent.parent/'bind_reset.json'
    metadata.write_text(json.dumps(dict(release='wavefront',max_release=5,
        release_qualification=dict(verdict='PENDING'),parts=dict(p=dict(core_release={'child.rst_n':None})),
        unreachable=[],long_hops=[])))
    with pytest.raises(SystemExit,match='native reset release is PENDING'):
        bind_smoke.qc_reset_contract(top,[])
