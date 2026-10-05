import copy,hashlib,json,math,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_minimum_protected_group as group
from dsrom_s81_leaf_fanout_construct import construct
NS=ROOT/group.NS
@pytest.fixture(scope='module')
def m():return group.verify(ROOT)
def test_positive_codec_cuts(m):
    assert {n:c['serial_held_edges'] for n,c in m['mutable_codec']['cuts'].items()}==dict(encode=1,decode=2,equal83=1,merge256=1)
    for c in m['mutable_codec']['cuts'].values():
        assert c['FF_hold_ps_after25unc_and25adverse_skew']>0
        assert c['serial_remaining_wire_ps_after25skew']>0
        assert c['streaming_remaining_wire_ps_after25skew']>0
    assert 0<m['mutable_codec']['cuts']['decode']['streaming_remaining_wire_ps_after25skew']<10

def test_full_II_does_not_free_at_write_or_local_receipt(m):
    s=m['service'];assert s['bank_service_II_slow_edges']==28
    assert s['local_RMW_edges']==14
    assert s['occupied_bank_ns_bound']>s['local_RMW_ns']
    assert s['bank_service_II_ns']>=s['occupied_bank_ns_bound']
    assert s['active_RMW_capacity_per_bank']==1
    assert s['counted_return_fast_edges']==9 and s['reverse_release_slow_edges']==7
    assert m['WQD4_max_service']['predecessor_wait_ns']==pytest.approx(3*28/.9)
@pytest.mark.parametrize('ahead',[-1,4,1.0,None])
def test_unbound_or_overcapacity_rejected(ahead):
    with pytest.raises(ValueError):group.service(ahead)
def test_one_fixed_route():
    with pytest.raises(ValueError):group.service(route_stations=15)
def test_no_unchecked_ckv_grant(m):
    p=m['ports'];assert p['check_1RW_mutually_exclusive_windows']==['old_read','write','postverify']
    assert p['instances']=={'data':12,'check':12}
    assert p['first_consumer']['src']==419776 and p['first_consumer']['n']==320
    assert 'not accept' in p['CKV_DMA_read_priority']
    assert m['read_service']['total_slow_edges_candidate']==12
    assert m['area']['held_arbitration_coded_FF']==1584
    assert 'drained' in m['read_service']['pending_write_forwarding']
def test_real_macro_clocks_and_check_cost_once(m):
    assert m['area']['check_macros_body_mm2']==pytest.approx(.01418015808)
    assert m['macro_corners']['data']['ss']['clk_to_q_ps']==pytest.approx(511.3577744831065)
    assert m['macro_corners']['check']['ss']['clk_to_q_ps']==pytest.approx(435.8338961206011)
    assert m['area']['joint_r4_not_summed']
    assert m['area']['replaced_exact_controller_bare_codec_floor_mm2']>0
    assert m['slot']['macro_CLK_SS_load_fF']==pytest.approx(24*8.68376)
def test_local_macro_halos_disjoint(m):
    ps=m['slot']['macro_instances'];assert len(ps)==24
    rects=[]
    for p in ps:
        a,b,c,d=p['macro_bbox_um'];h=p['halo_um'];rects.append((a-h,b-h,c+h,d+h))
    for i,(a,b,c,d) in enumerate(rects):
        for A,B,C,D in rects[:i]:assert c<=A+1e-8 or C<=a+1e-8 or d<=B+1e-8 or D<=b+1e-8
    assert max(r[3] for r in rects)<=m['slot']['macro_zone_height_um']+1e-8
    assert m['slot']['actual_unblocked_tracks'] is None
    assert m['slot']['parent_reticle_fit'] is None
def test_no_rate_or_context_signoff(m):
    assert m['unified_S81']['headline_token_rate'] is None
    assert m['unified_S81']['token_delta_us'] is None
    assert not m['admission']['engine_RTL_admitted']
    assert not m['admission']['group_PnR_admitted']
@pytest.mark.parametrize('name',['encode','decode','equal83','merge256'])
def test_retained_buffer_contraction(name):
    old=json.loads((NS/'evidence/original_registered_FAIL'/name/'mapped.json').read_text())
    new,proof=construct(old,capture_buffer=True)
    assert proof['clock_nets_unchanged'] and proof['logic_and_register_connections_equal_after_buffer_contraction']
    assert len(new['modules']['leaf']['cells'])>=len(old['modules']['leaf']['cells'])
@pytest.mark.parametrize('en,d,q',[(e,d,q) for e in [0,1] for d in [0,1] for q in [0,1]])
def test_held_landing_gate_truth(en,d,q):
    nand=lambda a,b:1-(a&b)
    assert nand(nand(d,en),nand(q,1-en))==(d if en else q)
def test_original_failure_retained():
    p=NS/'evidence/original_registered_FAIL/decode/ss.log';s=p.read_text()
    assert '848.20' in s and '59.19' in s and '(VIOLATED)' in s
    selected=json.loads((NS/'evidence/selected_held_landing/record.json').read_text())
    for v in selected['results'].values():
        for c in ['ss','ff']:assert not v['timing'][c]['electrical_violations']
    assert selected['results']['decode']['timing']['ss']['setup_slack_ps']<0
