import copy,gzip,json,os,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_native_weight_address_join as J
import dsrom_full_owner_compiler as C
import dsrom_owner_cfg_interface_export as E

@pytest.fixture(scope='module')
def joined():
    demand=json.load(gzip.open(J.D/'inputs/demand-r5.json.gz','rt'))
    return J.Join(demand,list(C.readrows(J.PHASES)))


def test_original_emitter_independent_all40_head_and_patches():
    p=subprocess.run([sys.executable,str(ROOT/'tools/dsrom_native_weight_source_reemit.py')],cwd=ROOT,text=True,capture_output=True,timeout=60,
      env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
    assert p.returncode==0,p.stderr
    x=json.loads(p.stdout);assert x['instructions']==4778 and x['patched_weight_instructions']==1149


def test_every_node_and_instruction_classified(joined):
    bs=[joined.binding(n) for n in joined.nodes]
    assert len(bs)==4887
    assert sum(b.get('address_bound',False) for b in bs)==1149
    assert sum(b['classification']=='UNBOUND_DEDICATED_HEAD' for b in bs)==1
    assert sum(n['kind']=='instruction' for n in joined.nodes.values())==4778
    reachable={(b['layer'],c['alias']) for b in bs for c in b.get('phase_choices',[])}
    assert reachable==set(joined.phases) and len(reachable)==46509


def test_two_wo_a_groups_and_shared_q_mode_not_owner_alias(joined):
    a=joined.binding('L0.I37');b=joined.binding('L0.I38');q=joined.binding('L0.I53')
    assert a['address_patches']['me_wbase']=={'old':0,'new':5<<16}
    assert b['address_patches']['me_wbase']=={'old':65536,'new':6<<16}
    assert q['address_patches']['qe_wbase']=={'old':0,'new':6<<16}
    assert b['phase_choices'][0]['source_key_word']!=q['phase_choices'][0]['source_key_word']


def test_actual_eid_vm_slot_not_tag_only(joined):
    b=joined.binding('L0.I66')
    assert b['selector_VM_element_address']==366688 and b['selector_slot']==0
    assert b['address_patches']['qe_istride']=={'old':1,'new':4096}
    f,c=joined.patched('L0.I66',[10,11,12,13,14,383])
    assert f['qe_ibase']==366688 and f['qe_wbase']+10*f['qe_istride']==c['source_key_word']&((1<<30)-1)
    assert c['alias']=='exp10.w1'


@pytest.mark.parametrize('ids',[[0,0,2,3,4,5],[5,4,3,2,1,0],[-1,1,2,3,4,5],[0,1,2,3,4,384],[0,1,2,3,4],[0.,1,2,3,4,5]])
def test_invalid_runtime_selection_fails(joined,ids):
    with pytest.raises(ValueError):joined.select('L0.I66',ids)


def test_all384_have_legal_sorted_selection_and_bound_concrete_branch(joined):
    nodes={joined.binding(n)['selector_slot']:n for n in joined.nodes if n.startswith('L0.') and joined.binding(n).get('alias')=='exp0.w1'}
    assert set(nodes)==set(range(6))
    for expert in range(384):
        ids=sorted({expert,*range(5)})
        if len(ids)<6:ids=list(range(6))
        slot=ids.index(expert)
        c=joined.select(nodes[slot],ids)
        assert c['alias']==f'exp{expert}.w1'


def test_current_native_predicate_failure_preserved(joined):
    assert joined.binding('L2.I24')['native_admission_failures']==['round']
    with pytest.raises(ValueError,match='m_ok'):joined.select_native_legal('L2.I24')
    assert joined.select_native_legal('L0.I37')['alias']=='wo_a.group0'
    with pytest.raises(ValueError):joined.select('Lhead.I5')


def test_stale_base_and_bad_selector_slot_controls(joined):
    j=copy.copy(joined);j.nodes=copy.deepcopy(joined.nodes)
    j.nodes['L0.I66']['instruction']['qe_wbase']=1
    with pytest.raises(ValueError,match='placeholder'):j.binding('L0.I66')
    j.nodes['L0.I66']['instruction']['qe_wbase']=0
    j.nodes['L0.I66']['instruction']['qe_ibase']+=1
    with pytest.raises(ValueError,match='selector'):j.binding('L0.I66')


def test_wrong_shape_and_format_controls(joined):
    j=copy.copy(joined);j.nodes=copy.deepcopy(joined.nodes)
    j.nodes['L0.I7']['instruction']['qe_nb']=159
    with pytest.raises(ValueError,match='shape'):j.binding('L0.I7')
    j.nodes['L0.I7']['instruction']['qe_nb']=160;j.nodes['L0.I7']['instruction']['qe_fp4']=1
    with pytest.raises(ValueError,match='format'):j.binding('L0.I7')


def test_duplicate_phase_key_and_wrong_mode_controls(joined):
    ps=list(joined.phases.values())
    with pytest.raises(ValueError,match='duplicate'):J.Join(joined.demand,[ps[0],ps[0]])
    bad=copy.deepcopy(ps[0]);bad['source_key_word']^=1<<30
    with pytest.raises(ValueError,match='opcode'):J.Join(joined.demand,[bad])
    bad=copy.deepcopy(ps[0]);bad['config_logical_word_range']=[1,26]
    with pytest.raises(ValueError,match='configuration'):J.Join(joined.demand,[bad])


def test_concrete_physical_rank_source_address_and_wrong_owner(joined):
    m=next(C.readrows(J.JOURNAL));p=joined.phases[(m['layer'],m['alias'])]
    addresses=[J.physical_address(m,p,r,0,0) for r in range(4)]
    assert [a['tensor_row'] for a in addresses]==[0,320,640,960]
    assert len({(a['stage'],a['pair'],a['mb'],a['physical_row'],tuple(a['bit_range'])) for a in addresses})==1
    assert addresses[0]['scale_physical_bit_range']==[256,264]
    assert addresses[0]['configuration']['last_word']['logical_address']==24
    for rank,row,k in [(4,0,0),(0,320,0),(0,0,5120)]:
        with pytest.raises(ValueError):J.physical_address(m,p,rank,row,k)
    with pytest.raises(ValueError,match='owner'):J.physical_address(m,{**p,'stage':p['stage']+1},0,0,0)
    changed=copy.deepcopy(m);changed['plans'][0][5]+=2
    with pytest.raises(ValueError,match='plan'):J.physical_address(changed,p,0,0,0)


def test_generated_complete_addresses_words_and_failed_native_not_claimed():
    r=J.D/'r3';x=json.loads((r/'model.json').read_text())
    assert not x['cfg_ECC_raw_provider_calendar_or_whole_token_qualified']
    assert len(x['native_admission_failures'])==7
    assert sum(1 for _ in C.readrows(r/'physical_address_boundaries.jsonl.gz'))==46509
    words=list(C.readrows(r/'patched_weight_words.jsonl.gz'))
    assert len(words)==1149 and all(len(w['word_hex'])==512 and not w['native_execution_qualified'] for w in words)


def test_pinned_archived_source_closure():
    h=json.loads((J.D/'inputs/reemit_source_hashes.json').read_text())
    assert all(J.sha(J.D/'inputs/source'/p)==s for p,s in h.items())
    select=(J.D/'inputs/source/rtl/hdc/v41/ot_hdc_select.sv').read_text()
    assert 'parameter integer ORDER = 1' in select
    adapt=(J.D/'inputs/ot_v41_rom_adapt.sv').read_text()
    assert "key <= key + AW'(vi_q) * stride" in adapt and 'if (!m_ok) fault' in adapt
