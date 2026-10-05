import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_allphase_resources import phase_resources


def event(eid,op,dst=None,producer=None,warp=0):
    return {'id':eid,'opcode':op,'active_lanes':[{'warp':warp,'lanes':[0]}],
        'dependencies':[] if producer is None else [producer],
        'operand_register_bindings':[] if producer is None else [{'operand_index':0,'register':'r','warp':warp,'lane':0,'source_lane':0,'producer_event':producer,'result_id':producer+':r'}],
        'result_register_bindings':[] if dst is None else [{'register':dst,'warp':warp,'lane':0,'result_id':eid+':'+dst}]}


def phase(kernel,events):return {'kernel':kernel,'shape':[1,32],'events':events}


def test_crossphase_memory_consumer_binds_actual_store_address_version():
    m=event('m','MOV','r');s=event('s','STORE',producer='m')
    s['source_mapped_shared_accesses']=[{'warp':0,'lane':0,'address':0,'bytes':4}]
    l=event('l','LOAD','x');l['source_mapped_shared_accesses']=[{'warp':0,'lane':0,'address':0,'bytes':4}]
    l['crossphase_shared_producer_bindings']=[{'consumer_warp':0,'consumer_lane':0,'producer_event':'s'}]
    phases=[phase('writer',[m,s]),phase('reader',[l])]
    assert phase_resources(phases,2)['shared_producer_audit_issues']==[]
    l['source_mapped_shared_accesses'][0]['address']=4
    assert 'shared_producer_version_or_address_mismatch:l' in phase_resources(phases,2)['shared_producer_audit_issues']


def test_mutually_exclusive_phase_scenarios_not_summed_or_memory_joined():
    a=event('a','LOAD','r');b=event('b','LOAD','r')
    d=phase_resources([phase('finite',[a]),phase('fallback',[b])],1)
    assert d['separate_branch_resource_totals']['finite']['RF_write_bits']==32
    assert d['separate_branch_resource_totals']['exceptional']['RF_write_bits']==32
    assert d['whole_program_cycles'] is None


def test_source_warp32_requires_second_range_not_silent_residency_remap():
    d=phase_resources([phase('large',[event('a','MOV','r',warp=0),event('b','MOV','r',warp=32)])],1)
    p=d['phases'][0]
    assert p['minimum_contiguous_resident_waves_capacity_only']==2
    assert not p['single_wave_residency_aperture'] and p['candidate_cycles'] is None
    assert 'resident_warp_limit' in p['calendar_blockers']
