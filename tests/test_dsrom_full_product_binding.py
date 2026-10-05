"""Compiler mutations and finite scheduling; synthetic cases give no product credit."""
import copy
import itertools
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_full_product_binding as B

@pytest.fixture(scope='module')
def demand():
    return B.prepare()

def test_actual_full_emitter_preserved(demand):
    p = demand['functional_program']
    assert sum(len(s['instructions']) for s in p['stages']) == 4771
    assert len(p['head']['instructions']) == 7
    assert B.F.validate_program(p)
    assert len([n for n in demand['nodes'] if n['kind'] == 'instruction']) == 4778
    assert len([n for n in demand['nodes'] if n['kind'] == 'consumer_done_fence']) == 41
    assert demand['historical_candidate_verdict'] == 'FAIL_CORRECTED_CAPACITY'
    for node in demand['nodes']:
        if node['kind'] == 'instruction':
            B.encode_instruction(node['instruction'])
    assert not any(demand['readiness'].values())

@pytest.mark.parametrize('scope', [2, 14, 20, 24, 36])
def test_actions_not_dropped_or_encoded_as_fake_opcodes(demand, scope):
    actual = [n['action'] for n in demand['nodes'] if n['scope'] == scope and n['kind'] == 'runtime_action']
    assert actual == demand['functional_program']['stages'][scope]['runtime_actions']

def atom(i, areas):
    return {'id': str(i), 'area_um2_by_rank': areas, 'tensor_assignment_receipts': ['synthetic-test-only']}

def test_minimum_contiguous_pack_against_exhaustive_small_cases():
    for vals in itertools.product(range(1, 4), repeat=5):
        atoms = [atom(i, [v]*4) for i,v in enumerate(vals)]
        result = B.pack_ordered(atoms, 5)
        minimum = 5
        for cuts in itertools.product((False, True), repeat=4):
            groups, current = [], [vals[0]]
            for cut, v in zip(cuts, vals[1:]):
                if cut: groups.append(current); current = []
                current.append(v)
            groups.append(current)
            if all(sum(g) <= 5 for g in groups): minimum = min(minimum, len(groups))
        assert len(result) == minimum

def test_owner_grain_and_rank_bottleneck():
    assert len(B.pack_ordered([atom(0,[1,4,1,1]),atom(1,[1,2,1,1])],5)) == 2
    with pytest.raises(ValueError,match='exceeds'): B.pack_ordered([atom(0,[1,6,1,1])],5)
    with pytest.raises(ValueError,match='duplicate'): B.pack_ordered([atom(0,[1]*4)]*2,5)

def ledger():
    return {'width_um':26000,'height_um':33000,'full_return_storage_bits':138469120,
            'service_replication_receipts':['synthetic-test-only'],
            'debits':[{'id':cat,'category':cat,'area_um2':area,'source_receipts':['synthetic-test-only']}
                      for cat,area in [('service',200000000),('routing_clock_PG',3000000),('return',104981748.0192)]]}

def test_reservation_return_and_duplicate_guards():
    x=ledger(); assert float(B.field_capacity(x)) == pytest.approx(550018251.9808)
    x['debits'].append(x['debits'][0])
    with pytest.raises(ValueError,match='duplicate'): B.field_capacity(x)
    x=ledger(); x['full_return_storage_bits']=0
    with pytest.raises(ValueError,match='omitted'): B.field_capacity(x)
    x=ledger();x['debits'][2]['area_um2']=1
    with pytest.raises(ValueError,match='discount'): B.field_capacity(x)
    x=ledger();x['width_um']=34712
    with pytest.raises(ValueError,match='manufacturing'): B.field_capacity(x)

def synthetic():
    d={'nodes':[{'id':'a','scope':0,'kind':'instruction','instruction':{'unit':B.F.I.UNIT_ME,'me_wbase':0}},
                {'id':'b','scope':0,'kind':'instruction','instruction':{'unit':B.F.I.UNIT_SU,'wait':1}},
                {'id':'f','scope':0,'kind':'consumer_done_fence'}]}
    alloc={'schema':'opentallas.dsrom.full-product-allocation.v1','demand_sha256':B.digest(d),
           'coverage_receipts':['synthetic-test-only'],'ordered_grains':[atom(0,[1]*4)],
           'capacity_ledger':ledger(),'bindings':{}}
    for rank in range(4):
        for n in d['nodes']:
            nid=f"{n['id']}.R{rank}"
            deps=[] if n['id']=='a' else [f'a.R{rank}'] if n['id']=='b' else [f'a.R{rank}', f'b.R{rank}']
            alloc['bindings'][nid]={'semantic_sha256':B.digest(n),'owner_grain':'0','provider':n['id'],
                'source_receipts':['synthetic-test-only'],'native_ISA_provider_contract':['synthetic-test-only'],
                'calendar':{'domain':'streaming','accept_cycles':1,'complete_cycles':12 if n['id']=='a' else 1,
                            'issue_interval_cycles':2,'completion_dependencies':deps,'source_receipts':['synthetic-test-only']}}
    return d,alloc

def test_causal_completion_and_finite_II():
    d,a=synthetic(); out=B.compose(d,a,fixture_only=True); ev={e['id']:e for e in out['events']}
    assert ev['b.R0']['start_ns']==10
    assert ev['f.R0']['start_ns']==pytest.approx(10+5/6)
    assert len(out['ISA_images']['0'])==2
    assert not out['readiness']['physical_admission']

@pytest.mark.parametrize('mutation', ['missing','semantic','arithmetic','wait','unknown','cycle','adapter','unsourced'])
def test_binding_mutations_refused(mutation):
    d,a=synthetic(); b=a['bindings']['b.R0']
    if mutation=='missing':del a['bindings']['a.R0']
    elif mutation=='semantic':b['semantic_sha256']='wrong'
    elif mutation=='arithmetic':b['address_patches']={'su_nin':{'old':1,'new':2}}
    elif mutation=='wait':b['calendar']['completion_dependencies']=[]
    elif mutation=='unknown':b['calendar']['complete_cycles']=None
    elif mutation=='cycle':a['bindings']['a.R0']['calendar']['completion_dependencies']=['b.R0']
    elif mutation=='adapter':b['native_ISA_provider_contract']=[]
    else:b['calendar']['source_receipts']=[]
    with pytest.raises((ValueError,TypeError)): B.compose(d,a,fixture_only=True)

def test_cross_rank_dependency_is_not_free():
    d,a=synthetic();a['bindings']['a.R1']['calendar']['complete_cycles']=24
    a['bindings']['b.R0']['calendar']['completion_dependencies'].append('a.R1')
    events={e['id']:e for e in B.compose(d,a,fixture_only=True)['events']}
    assert events['b.R0']['start_ns']==20


def test_production_refuses_synthetic_source_receipts():
    with pytest.raises(ValueError,match='receipt needs'):
        B.verify_input_receipts(synthetic()[1])

def test_committed_receipt_hash_identity_and_payload_refusal():
    pin=B.source_pins()[0]
    assert B.verify_input_receipts({'coverage_receipts':[pin]}) == [pin]
    bad=copy.deepcopy(pin);bad['sha256']='wrong'
    with pytest.raises(ValueError,match='byte mismatch'):
        B.verify_input_receipts({'coverage_receipts':[bad]})
    bad['path']='checkpoint.safetensors'
    with pytest.raises(ValueError,match='payload'):
        B.verify_input_receipts({'coverage_receipts':[bad]})

def test_compiled_np_changes_return_not_active_mask():
    t={'compiled_NP':8192,'R':128,'NBF':1024,'RD':64,'ROOTD':128,'RST':1}
    old=B.return_dimensions(t)
    assert old['declared_lower_bits']==138469120
    assert old['conservative_FF_50pct_um2']==pytest.approx(104981748.0192)
    t['active']=3375
    assert B.return_dimensions(t)==old
    t['compiled_NP']=4096
    new=B.return_dimensions(t)
    assert new['declared_lower_bits']==69771008
    assert new['conservative_FF_50pct_um2']==pytest.approx(52897587.42528)
    assert new['tree_levels']==old['tree_levels']-1
    x=ledger();x['compiled_return_topology']=t;x['full_return_storage_bits']=new['declared_lower_bits']
    x['debits'][2]['area_um2']=new['conservative_FF_50pct_um2']
    with pytest.raises(ValueError,match='padding'):B.field_capacity(x)
    x['compiled_topology_binding_receipts']=['synthetic-test-only']
    assert B.field_capacity(x)>B.field_capacity(ledger())

def test_source_return_equations_match_owner(demand):
    assert demand['return_source']['commit'].startswith('3995d7208')
    assert demand['return_source']['status']=='DECLARED_STATE_SCALES_WITH_COMPILED_TOPOLOGY_NOT_ACTIVE_WORKLOAD_CREDIT'

def test_complete_all40_calendar_and_words_without_payload(demand):
    a={'schema':'opentallas.dsrom.full-product-allocation.v1','demand_sha256':B.digest(demand),
       'coverage_receipts':['synthetic-test-only'],'ordered_grains':[atom(0,[1]*4)],
       'capacity_ledger':ledger(),'bindings':{}}
    for r in range(4):
        scope=None; last={}; scope_nodes=[];previous=None
        for n in demand['nodes']:
            nid=f"{n['id']}.R{r}"
            if scope!=n['scope']:
                scope=n['scope'];last={};scope_nodes=[]
            deps=set(last.values())
            if previous:deps.add(previous)
            if n['kind']=='consumer_done_fence' or (n['kind']=='instruction' and n['instruction']['unit']==B.F.I.UNIT_END):
                deps.update(scope_nodes)
            a['bindings'][nid]={'semantic_sha256':B.digest(n),'owner_grain':'0','provider':str(n.get('instruction',{}).get('unit', 'service')),
                'source_receipts':['synthetic-test-only'],'native_ISA_provider_contract':['synthetic-test-only'],
                'calendar':{'domain':'streaming','accept_cycles':1,'complete_cycles':2,'issue_interval_cycles':1,
                            'completion_dependencies':sorted(deps),'source_receipts':['synthetic-test-only']}}
            if n['kind']=='instruction':last[n['instruction']['unit']]=nid
            scope_nodes.append(nid);previous=nid
    out=B.compose(demand,a,fixture_only=True)
    assert len(out['events'])==4*len(demand['nodes'])
    assert all(len(words)==4778 for words in out['ISA_images'].values())
    assert out['synthetic_fixture_only']
    assert not out['readiness']['full_token_rate']

def test_padding_is_charged_and_BF_mask_not_workload():
    a={'capacity_ledger':ledger(),'compiled_field':{'NP':8192,'NBF':1024,'physical_macros_per_pair':4,'source_receipts':['synthetic-test-only']},
       'ordered_grains':[dict(atom(0,[1]*4),q_pairs_by_rank=[2651]*4,BF_pairs_by_rank=[724]*4)]}
    groups=B.pack_ordered(a['ordered_grains'],858000000)
    result=B.validate_padding(a,groups,858000000)
    assert result[0]['q_padding']==4517 and result[0]['BF_padding']==300
    assert result[0]['physical4096_macro_count']==32768
    with pytest.raises(ValueError,match='padding exceeds'):B.validate_padding(a,groups,1)
    a['compiled_field']['NP']=4096
    with pytest.raises(ValueError,match='mismatch'):B.validate_padding(a,groups,858000000)
