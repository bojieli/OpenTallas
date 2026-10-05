"""All-PC metadata closure, exact missing-input guards; no numeric prefix."""
import collections
import copy
import gzip
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_full_checkpoint_continuation_plan as P


def test_complete_contiguous_source_required():
    with pytest.raises(ValueError,match='complete contiguous'):
        P.source_rows({'instructions':[],'templates':{}},[],{},lambda p:{})


@pytest.mark.parametrize('spec',[{'shape':[None],'dtype':'F32'}, {'shape':[-1],'dtype':'F32'}, {'shape':[1],'dtype':'U8'}])
def test_unknown_shape_type_cannot_be_zero_cost(spec):
    with pytest.raises(ValueError):P.shape_size(spec)


def test_exact_missing_dynamic_weight_aux_and_generated_ownership():
    op={'pc':20,'family':'expert_fetch'};manifest={'generation':1,'checkpoint_revision':'rev','view_bindings':{}}
    assert P.missing_binding(op,'t','table',{'kind':'explicit_auxiliary_provider'},manifest)=='EXPLICIT_AUXILIARY_SOURCE_UNBOUND'
    assert P.missing_binding({'pc':21,'family':'linear_q'},'t','w',{'kind':'immutable_weight_provider','logical_tensor':[0,'w1']},manifest) is None
    assert P.missing_binding({'pc':12,'family':'all_gather'},'t','ownership_mask',{'kind':'explicit_auxiliary_provider'},manifest) is None
    assert P.missing_binding(op,'t','p',{'kind':'immutable_parameter_provider','logical_tensor':'norm'},manifest) is None


def test_home_union_retains_raw_contents_and_two_copies():
    homes=[{'birth_pc':0,'rank_group':[0],'SM':0,'home':{'class':'RF','slot_first':0,'vectors':1}},
           {'birth_pc':1,'rank_group':[0],'SM':0,'home':{'class':'RF','slot_first':0,'vectors':1}},
           {'birth_pc':2,'rank_group':[0],'SM':0,'home':{'class':'RF','slot_first':1,'vectors':1}}]
    result=P.home_inventory(homes,{'initial_versions':[]},2)
    assert result['resident_sector_upper']==2*2*512//32
    assert result['serialized_sector_payload_upper_bytes']==46*result['resident_sector_upper']
    assert result['persisted_raw_contents_not_reclaimed_on_version_release']
    assert result['actual_checkpoint_bytes'] is None


def test_enrolled_source_mutant_fails_before_read_or_constructor(monkeypatch):
    monkeypatch.setattr(P,'PINS',{'tools/ds_producer_checkpoint_resume_v3.py':'0'*64})
    with pytest.raises(ValueError,match='source drift'):P.generate()


def model():
    return P.load(ROOT/'results/uarch/ds_full_checkpoint_continuation_plan_20261003/r6/model.json')


def test_actual_program_all_PC_family_and_output_closure():
    m=model();native=P.load(ROOT/P.NATIVE)
    assert m['PCs']==2213 and len(m['families'])==30
    assert m['families']==dict(collections.Counter(o['family'] for o in native['instructions']))
    assert [r['PC'] for r in m['rows']]==list(range(2213))
    assert len(m['rows'][11:])==2202
    for op,row in zip(native['instructions'],m['rows']):
        assert (row['PC'],row['family'],row['dependencies'])==(op['pc'],op['family'],op['dependencies'])
        calls=sum(len(r.get('buffer_programs',[])) or 1 for r in op['rank_bindings'] if not r.get('empty_owned_extent'))
        assert calls==row['native_calls']
        assert row['numeric_status']=='NOT_EXECUTED_BY_THIS_PLAN'


def test_all_remaining_milestones_cover_every_PC_without_holes():
    m=model();stages=m['milestones'];pcs=[]
    for s in stages:pcs.extend(range(s['first_PC'],s['last_PC']+1))
    assert pcs==list(range(11,2213))
    assert (stages[0]['first_PC'],stages[0]['last_PC'])==(11,19)
    assert (stages[1]['first_PC'],stages[1]['last_PC'])==(20,20)
    assert stages[-1]['last_PC']==2212
    assert m['whole_resource_admission'] is False and m['full_token_numerical_pass'] is None
    assert all(s['whole_journal_bytes'] is None for s in stages)


def test_known_component_counts_are_positive_and_unknowns_remain_unknown():
    m=model();s=m['milestones'][0]
    for name in ('native_calls','sector_requests_component_upper','CPU_native_live_and_transient_bytes',
                 'conservative_sector_journal_component_bytes','fresh_journal_bootstrap_component_bytes',
                 'old_and_restored_sector_heap_component_bytes','two_cold_source_graph_heap_component_bytes'):
        assert type(s[name])is int and s[name]>0
    assert s['checkpoint_sector_inventory']['AW']==27
    assert not s['cold_metadata_and_RAM_complete']
    assert len(m['dynamic_weight_source_dependencies'])==2246
    assert m['effective_weight_view_source']=='tools/h3_ds_checkpoint_provider_r33.py'


def test_retained_resource_count_mutant_refuses(tmp_path):
    wrong=tmp_path/'tampered.json';wrong.write_text('{}')
    with pytest.raises(ValueError,match='exact retained'):P.reconcile_from_retained(wrong)

def test_refined_collective_masks_are_generated_not_sector_reads():
    m=model()
    for r in m['rows']:
        if r['family'] in ('all_gather','all_reduce'):
            assert r['collective_generated_mask_sector_requests']==0
            assert r['source_owned_sector_request_component_upper']>=0
    next=m['milestones'][0]
    assert next['source_owned_sector_request_component_upper']==3132192
    assert next['source_owned_conservative_sector_journal_component_bytes']==141124042752
    assert m['binding_gap_counts']=={'COMPOSITE_WEIGHT_SOURCE_HANDLER_UNBOUND':6}
    assert m['audit_correction']
    assert 'r31 exact BF16 selected-row weight_view' in m['source_handler_counts']


def test_actual_composed_MRO_retains_existing_reader_paths():
    m=model()
    files={r['source'] for r in m['composed_provider_MRO']}
    assert 'tools/h3_ds_checkpoint_provider_r31.py' in files
    assert 'tools/h3_ds_checkpoint_provider_r33.py' in files
    assert 'tools/h3_ds_history_provider_r36.py' in files
    assert 'tools/ds_hbm_source_merge_r37.py' in files
    assert len(m['auxiliary_manifest_absence_resolved_by_actual_source_hooks'])==288
    assert {g['PC'] for g in m['missing_provider_bindings']}=={115,443,776}
    assert all(b['actual_route_or_shared_source_binding_pass'] is None for b in m['dynamic_weight_source_dependencies'])

def test_query_fields_and_absolute_finite_apertures_priced_separately():
    m=model();last=m['milestones'][-1]['checkpoint_sector_inventory']
    assert last['query_field_home_count']>0 and last['query_field_sector_component_upper']>0
    assert last['all_declared_home_and_query_sector_component_upper']>=last['resident_sector_upper']
    assert last['all_finite_RF_state_shared_aperture_sector_upper']==96*((16<<20)+(32<<20)+32*65536)//32
    assert m['next_implementation_gate']['whole_completion_PC_end']==2212
    assert 'NOT an allowed' in m['next_implementation_gate']['strict_V3_identity']


def test_actual_composite_descriptor_rejected_without_payload_or_constructor():
    from h3_ds_checkpoint_provider_r33 import Provider
    native=P.load(ROOT/P.NATIVE)
    op=native['instructions'][115]
    required=next(b for bs in op['provider_bindings'].values() for b in bs.values() if b['kind']=='immutable_weight_provider')
    stub=type('SourceOnly',(),{'native':native,'_weight_op':Provider._weight_op})()
    with pytest.raises(ValueError,match='exact native weight call identity required'):
        Provider.weight_view(stub,'weight',required,op['rank_bindings'][0],{})
    assert P.missing_binding(op,'t','weight',required,{})=='COMPOSITE_WEIGHT_SOURCE_HANDLER_UNBOUND'


def test_automatic_contiguous_scope_selection_does_not_grant_admission():
    m=model();retired=list(range(11))
    visited=[]
    while len(retired)<2213:
        req=P.next_scope_request(m,retired,'/old','/new')
        assert req['first_PC']==len(retired)
        assert not req['execution_authorized_by_this_helper'] and not req['repeat_retired_prefix']
        visited.extend(range(req['first_PC'],req['prefix_stop']+1))
        retired=list(range(req['prefix_stop']+1))
    assert visited==list(range(11,2213))
    assert P.next_scope_request(m,retired,'/old','/new')['complete']
    for bad in ([0,2],list(range(10)),[True]):
        with pytest.raises(ValueError):P.next_scope_request(m,bad,'/old','/new')
    with pytest.raises(ValueError,match='fresh journal'):P.next_scope_request(m,list(range(11)),'/old','/old')
