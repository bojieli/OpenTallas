import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_slot_join as C


@pytest.fixture(scope='module')
def events(): return C.S.events('r2_PASS')


def test_actual_bank_depth_no_ready_peak_and_complete_row_debt(events):
    r=C.capture(events,C.bank_layout(events))
    assert r['peak_writes_per_edge']==128
    assert r['bank_depth_histogram']=={6:32,4:96}
    assert r['writer_bursts']=={415:128,416:128,417:128,418:128,419:32,420:32}
    assert r['captured_rows']==576 and r['source_healthy_terminal']==422
    assert r['exact_information_bits']==19009
    assert r['uniform_payload_occupancy_and_fault_bits']==25345
    assert r['uniform_extra_slots']==192


@pytest.mark.parametrize('mutation',['layout_alias','missing_credit','duplicate','wrong_port','wrong_data','late_capture','bool_slot','stale_epoch'])
def test_actual_capture_negative_controls_preserve_input(events,mutation):
    layout=C.bank_layout(events);ev=list(events)
    if mutation=='layout_alias': layout['0'],layout['1']=layout['1'],layout['0']
    elif mutation=='missing_credit': layout['0'].pop()
    elif mutation=='bool_slot': layout['0'][0]=False
    else:
        i=next(i for i,e in enumerate(ev) if e['kind']=='VM_write_accept');e=ev[i]=dict(ev[i])
        if mutation=='duplicate': e['b']=398722
        elif mutation=='wrong_port': e['a']=1
        elif mutation=='wrong_data': e['c']^=1
        elif mutation=='stale_epoch': e['reset_era']=1
        else: e['edge']=422
    before=copy.deepcopy(layout)
    with pytest.raises(ValueError):C.capture(ev,layout)
    assert layout==before


def proposed_slots(capture):
    # Explicit fake schedule tests model only; not actual transport callbacks.
    reads=[dict(row=row,edge=423+row) for row in range(576)]
    pubs=[dict(row=row,edge=1000+row,packet=row//128) for row in range(576)]
    ACKs=[dict(packet=packet,edge=max(p['edge'] for p in pubs if p['packet']==packet)+1) for packet in range(5)]
    return reads,pubs,ACKs,1577


def test_finite_reserved_slot_join_test_double(events):
    capture=C.capture(events,C.bank_layout(events));r,p,a,t=proposed_slots(capture)
    result=C.slot_join(capture,r,p,a,t)
    assert result['last_read']==998 and result['last_causal_ACK']==1576
    assert result['next_owner_accept_edge']==1577
    assert not result['actual_provider_measured']


@pytest.mark.parametrize('mutation',['read_before_health','same_edge_two_reads','missing_row','wrong_packet','missing_ACK','early_ACK','duplicate_publication','early_retire','bool_edge'])
def test_slots_need_capacity_complete_debt_and_causal_retirement(events,mutation):
    capture=C.capture(events,C.bank_layout(events));r,p,a,t=proposed_slots(capture)
    if mutation=='read_before_health':r[0]['edge']=422
    elif mutation=='same_edge_two_reads':r[1]['edge']=r[0]['edge']
    elif mutation=='missing_row':r.pop()
    elif mutation=='wrong_packet':a[0]['packet']=99
    elif mutation=='missing_ACK':a.pop()
    elif mutation=='early_ACK':a[0]['edge']-=1
    elif mutation=='duplicate_publication':p[1]['row']=p[0]['row']
    elif mutation=='early_retire':t=1576
    else:r[0]['edge']=True
    before=copy.deepcopy((r,p,a))
    with pytest.raises(ValueError):C.slot_join(capture,r,p,a,t)
    assert (r,p,a)==before


def test_archived_peer_slot_join_replays_without_private_peer_files():
    p=C.S.load(C.OUT/'Nash_proposed_slot_join.json')
    assert C.replay_proposal(p)==p['join']


@pytest.mark.parametrize('mutation',['phase_shift','credit_early'])
def test_peer_calendar_cannot_shift_source_body_or_drop_completion_ACK(mutation):
    p=C.S.load(C.OUT/'Nash_proposed_slot_join.json')
    if mutation=='phase_shift':p['proposed_remote_source_idle']-=1
    else:p['next_owner_credit_accept_floor']=p['completion_packet_ACK_accept']
    with pytest.raises(ValueError):C.replay_proposal(p)
