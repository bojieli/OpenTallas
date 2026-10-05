"""Synthetic receipts test software contracts; no runtime/provider qualification."""
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import pytest
import dsrom_I66_stage_dispatch as D


def command(eid=0,rank=0):
    return D.resolve(eid,rank,1,0,dict(accepted=True,address=366688,read_edge=11,response_edge=12,value=eid))


def test_exhaustive_384_experts_all_four_ranks():
    node,table=D.owner_table()
    for rank in range(4):
        for eid in range(384):
            c=command(eid,rank);p=table[eid]
            assert (c['owner_stage'],c['phase'],c['key_word'])==(p['stage'],p['phase'],p['source_key_word'])
            assert c['config_logical_word_range']==[p['phase']*25,(p['phase']+1)*25]
            assert c['ordered_K_grain']==[0,5120]
    assert command(383)['owner_stage']==1
    assert command(383)['phase']==285
    assert command(383)['key_word']==2151149568


@pytest.mark.parametrize('eid',[-1,384,512,True])
def test_invalid_eid_no_alias(eid):
    with pytest.raises(ValueError):command(eid)


@pytest.mark.parametrize('ids',[[0,1,2,3,4,4],[0,1,2,3,4,384],[1,0,2,3,4,5],[0]])
def test_selector_rejects_noncontract(ids):
    with pytest.raises(ValueError):D.selected_six(ids)


def test_actual_read_identity_and_rank():
    assert D.selected_six([0,2,3,7,80,383])==[0,2,3,7,80,383]
    for k,v in [('accepted',False),('address',0),('response_edge',13),('value',3)]:
        read=dict(accepted=True,address=366688,read_edge=11,response_edge=12,value=0);read[k]=v
        with pytest.raises(ValueError):D.resolve(0,0,0,0,read)
    with pytest.raises(ValueError):command(0,4)


def test_wrong_local_owner_and_occupied_credit():
    c=command(383);l=D.DispatchLedger()
    with pytest.raises(ValueError):l.accept(c,0,15)
    l.accept(c,1,15)
    with pytest.raises(ValueError):l.accept(command(),0,16)


def test_complete_causal_retirement_and_no_replay():
    c=command();l=D.DispatchLedger();l.accept(c,0,15)
    l.transport_accept(c,'input0');l.idle(c,422)
    with pytest.raises(ValueError):l.retire(c)
    for row in range(576):l.visible(c,row,398720+row,415,420)
    with pytest.raises(ValueError):l.retire(c)
    l.transport_ack(c,'input0');l.retire(c)
    assert l.retired
    with pytest.raises(ValueError):l.accept(c,0,500)


def test_stale_duplicate_address_and_ack():
    c=command();l=D.DispatchLedger();l.accept(c,0,15)
    stale=copy.deepcopy(c);stale['generation']=0
    with pytest.raises(ValueError):l.idle(stale,422)
    with pytest.raises(ValueError):l.visible(c,0,0,415,420)
    with pytest.raises(ValueError):l.visible(c,0,398720,415,414)
    l.visible(c,0,398720,415,420)
    with pytest.raises(ValueError):l.visible(c,0,398720,415,420)
    l.transport_accept(c,'p');l.transport_ack(c,'p')
    with pytest.raises(ValueError):l.transport_ack(c,'p')
    with pytest.raises(ValueError):l.transport_accept(c,'p')


def receipts(c):
    return dict(identity={k:c[k] for k in ['node','expert','rank','generation','user','owner_stage','phase','key_word']},actual_accepted=True,
                input_last_visible_edge=45,first_VM_read_edge=45,source_idle_edge=422,
                visible_rows=[dict(row=i,address=398720+i,write_edge=415,visible_edge=420) for i in range(576)],
                forward_debt=0,result_debt=0,last_transport_ACK_edge=430)


def test_unified_calendar_prices_completion_tail():
    c=command();m=D.compose(c,15,receipts(c))
    assert m['forwarding_edges']==3 and m['service_edges']==407
    assert m['completed_edge']==430 and m['completion_after_source_edges']==8
    assert not m['source_runtime_verified'] and not m['no_token_loss_proven']


@pytest.mark.parametrize('mutation',['owner','offered','input','missing','duplicate','debt','early_idle','address'])
def test_calendar_bad_receipt(mutation):
    c=command();r=receipts(c)
    if mutation=='owner':r['identity']['owner_stage']=1
    if mutation=='offered':r['actual_accepted']=False
    if mutation=='input':r['input_last_visible_edge']=46
    if mutation=='missing':r['visible_rows'].pop()
    if mutation=='duplicate':r['visible_rows'][-1]=r['visible_rows'][0]
    if mutation=='debt':r['result_debt']=1
    if mutation=='early_idle':r['source_idle_edge']=14
    if mutation=='address':r['visible_rows'][0]['address']=0
    with pytest.raises(ValueError):D.compose(c,15,r)


def test_source_link_finite_store_forward_price_not_selected():
    m=D.model();a=m['existing_stage_link_default_screen']['input'];b=m['existing_stage_link_default_screen']['result']
    assert a['flits']==640 and a['packet_flits']==[256,256,128]
    assert a['minimum_occupied_edges']==1283
    assert b['bits']==36288 and b['flits']==142 and b['minimum_occupied_edges']==285
    assert not a['actual_provider_selected']
    assert m['current_provider']['forwarding_width'] is None
    assert m['software_control']['new_hardware_storage_bits']==0


def test_source_phase_key_mutants_fail_closed(tmp_path,monkeypatch):
    import gzip,json
    inputs=tmp_path/'inputs';inputs.mkdir()
    for name in ['cfg_phase_directory.jsonl.gz','cfg_key_tables.jsonl.gz']:
        (inputs/name).write_bytes((D.OUT/'inputs'/name).read_bytes())
    path=inputs/'cfg_key_tables.jsonl.gz'
    with gzip.open(path,'rt') as f:keys=[json.loads(l) for l in f]
    keys[0]['words'][10]=0
    with gzip.open(path,'wt') as f:
        for row in keys:f.write(json.dumps(row)+'\n')
    D._source_table.cache_clear()
    with monkeypatch.context() as m:
        m.setattr(D,'OUT',tmp_path)
        with pytest.raises(ValueError,match='key/PHW'):D.owner_table()
    D._source_table.cache_clear()


def test_packet_ack_has_positive_edge_and_matching_identity():
    p=D.packet_screen(256)
    assert p['minimum_occupied_edges']==3
    assert p['minimum_reverse_ACK_edges_per_packet']==1
    assert p['reverse_packet_ACK_control_bits']==10
    assert p['ACK_does_not_prove_destination_visibility']
