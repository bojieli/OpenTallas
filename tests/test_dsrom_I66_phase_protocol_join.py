import copy
import importlib.util
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_phase_protocol_join as M
spec=importlib.util.spec_from_file_location('fixture',Path(__file__).with_name('test_dsrom_I66_slot0_phase_lease.py'))
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


def case():
    lease,samples=F.fixture()
    old=samples
    samples=[copy.deepcopy(old[0]) for i in range(3)]+old
    for i,s in enumerate(samples):
        s['edge']=i;s['post_edge']=i
        if i<3:
            s.update(ingress=None,writes=[],reads=[],X_tags=[],credit_returns=[],post_VM={})
    lease['release_edge']+=3
    journal=[]
    for r in range(576):
        v=3*r+3
        for k,t in [('read_accept_reserved',v-3),('registered_return',v-2),('consumer_accept',v-1),('home_visible',v),('credit_return_capture',v+2)]:
            e=dict(kind=k,row=r,time=str(t))
            if k=='read_accept_reserved':e['shard']=((r%256)//2)//64
            journal.append(e)
    return lease,samples,dict(lease['context']),journal


def test_one_phase_join_distinguishes_actual_SU_read_from_writer_delivery():
    l,s,c,j=case();m=M.join(l,s,c,j,2,2)
    assert m['protocol_rows']==576 and m['peak_source_credit_debt']==2
    assert not m['downstream_delivery_is_SU_read']
    assert not m['actual_source_enrollment']


@pytest.mark.parametrize('fault',['context','shard','visible_edge','credit_edge','sameedge_reply','capacity','partial','CDC_phase','unknown_event'])
def test_cross_journal_or_credit_association_rejected(fault):
    l,s,c,j=case();capacity=2
    if fault=='context':c['user']=0
    if fault=='shard':j[0]['shard']=1
    if fault=='visible_edge':j[3]['time']='4'
    if fault=='credit_edge':j[4]['time']='6'
    if fault=='sameedge_reply':j[1]['time']='2'
    if fault=='capacity':capacity=1
    if fault=='partial':j.pop(1)
    if fault=='CDC_phase':j[0]['time']='1/2'
    if fault=='unknown_event':j.append(dict(kind='busy_progress',row=0,time='1'))
    with pytest.raises(ValueError):M.join(l,s,c,j,2,capacity)


def test_actual_deadline_not_inferred_from_software_join():
    p=M.source_plan()
    assert p['C'] is None and p['actual_consumer_deadline'] is None
    assert not p['compiled_ingress_or_callback_available'] and not p['RTL_GO']


@pytest.mark.parametrize('user',[0,65535,65536,2**32-1])
def test_exact_selected_Nash_codec_not_just_width(user):
    fields=M.N.widths()['header_fields'];v={k:0 for k in fields}
    v.update(user=user,reserved=65535,generation=7)
    assert M.encode_header144(v)==M.N.encode(fields,v)
    assert M.decode_header144(M.encode_header144(v))==v


def test_c9_does_not_supply_unmeasured_phase_or_deadline():
    p=M.source_plan()
    assert p['selected_clock_phase_reset_release'] is None
    assert not p['selected_clock_qualified']
    assert p['selected_Arch_bank']['core_clock70406']==70406
    assert max(x['LSB']+x['width'] for x in p['header144_fields_LSB'])==144


def test_sameedge_posted_credit_not_available_to_preedge_issue():
    l,s,c,j=case()
    # Hold row0's credit one extra edge so it is captured at row2's issue edge.
    s[5]['credit_returns'].remove(0);s[6]['credit_returns'].append(0)
    j[4]['time']='6'
    with pytest.raises(ValueError,match='same-edge'):M.join(l,s,c,j,2,2)


@pytest.mark.parametrize('time',[False,1.0])
def test_malformed_source_event_time_rejected(time):
    l,s,c,j=case();j[0]['time']=time
    with pytest.raises(ValueError):M.join(l,s,c,j,2,2)
