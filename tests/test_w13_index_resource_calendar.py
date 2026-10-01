import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_resource_calendar import schedule,demand,build


def event(eid,op,dst=None,reads=(),lanes=(0,1),warp=0):
    operands=[{'operand_index':i,'register':r,'warp':warp,'lane':lane,'source_lane':lane,
               'producer_event':producer,'result_id':f'{producer}:{r}:{warp}:{lane}'}
              for i,(r,producer) in enumerate(reads) for lane in lanes]
    return {'id':eid,'opcode':op,'active_lanes':[{'warp':warp,'lanes':list(lanes)}],
        'dependencies':sorted({p for r,p in reads}), 'operand_register_bindings':operands,
        'result_register_bindings':[] if dst is None else [
            {'register':dst,'warp':warp,'lane':lane,'result_id':f'{eid}:{dst}:{warp}:{lane}'} for lane in lanes]}


def test_exact_active_RF_demand_and_two_cycle_import():
    events=[event('a','MOV','r'),event('b','IADD','s',[('r','a')])]
    contracts={'MOV':{'core_latency':1,'II':1},'IADD':{'core_latency':7,'II':1}}
    d=schedule(events,contracts,{})
    assert d['issues']==[] and d['candidate_cycles']==10
    assert d['calendar'][1]['RF_read_cycle']==1 and d['calendar'][1]['issue_cycle']==3
    assert d['demand']['active_RF_read_bits_by_opcode']=={'MOV':0,'IADD':64}
    assert d['demand']['active_RF_physical_two_copy_write_bits']==256


def test_shared_bank_conflicts_and_no_free_broadcast():
    events=[event('a','LOAD','r')]
    c={'LOAD':{'core_latency':2,'II':1}}
    conflict=schedule(events,c,{('a',0):[0,32]})
    clear=schedule(events,c,{('a',0):[0,1]})
    repeat=schedule(events,c,{('a',0):[0,0]})
    assert conflict['candidate_cycles']==4 and clear['candidate_cycles']==3
    assert repeat['candidate_cycles']==4


def test_unknown_contract_or_unbound_address_prohibits_timing():
    e=[event('a','LOAD','r')]
    d=schedule(e,{},{});assert d['calendar'] is None and d['candidate_cycles'] is None
    assert 'opcode_contract_missing:LOAD' in d['issues']
    assert 'shared_address_binding_missing:a' in d['issues']
    assert schedule(e,{'LOAD':{'core_latency':2,'II':1}},{('a',0):[0,16384]})['calendar'] is None


def test_stale_version_cannot_get_calendar():
    events=[event('a','MOV','r'),event('b','MOV','r'),event('c','IADD','s',[('r','a')])]
    d=schedule(events,{'MOV':{'core_latency':1,'II':1},'IADD':{'core_latency':7,'II':1}}, {})
    assert d['calendar'] is None
    assert any(x.startswith('stale_lane_version:') for x in d['issues'])


def test_store_visibility_precedes_other_warp_read_service():
    events=[event('a','MOV','r'),event('b','STORE',reads=[('r','a')]),event('c','LOAD','s',warp=1)]
    contracts={o:{'core_latency':3,'II':1} for o in ('MOV','LOAD','STORE')}
    d=schedule(events,contracts,{('b',0):[0,1],('c',1):[0,1]})
    assert not d['issues']
    assert d['calendar'][2]['shared_service_first_cycle']>=d['calendar'][1]['writeback_or_retirement_cycle']


def test_pinned_finite_manifest_has_source_demands_but_no_invented_timing():
    d=build()
    assert d['calendar'] is None and d['candidate_cycles'] is None
    assert d['demand']['executed_warp_issues_by_opcode']['IMUL']==256
    assert d['demand']['executed_warp_issues_by_opcode']['STORE']==2
    assert d['demand']['active_RF_read_bits_by_opcode']['STORE']==64
    assert not d['hardware_launch'] and d['whole_token_cycles'] is None
