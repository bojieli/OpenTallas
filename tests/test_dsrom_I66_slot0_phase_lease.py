import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_slot0_phase_lease as M


def fixture():
    ctx=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=7,user=65536,xversion=52,pc=66)
    records=[dict(row=r,pos=0,fp32=r+1,bf16=r,error=0) for r in range(576)]
    lease=dict(clock='native_core_clk',context=ctx,start_edge=0,release_edge=1730,records=records,
               descriptor=dict(fmt=1,rsplit=576,pw62=0,pw63=0,obase=398720,ops=576))
    samples=[]
    for edge in range(1731):
        s=dict(edge=edge,clock='native_core_clk',context=ctx,reset_accepted=True,healthy=True,
               sampled_writer_classes=list(M.V.WRITERS),parameters=dict(X_ROM=1,ROM_PHW=10,ROM_R=128,SUN=256,ROM_FBW=1632),
               ingress=None,writes=[],post_stage='postNBA',post_edge=edge,post_VM={},reads=[],X_tags=[],credit_returns=[])
        row,step=divmod(edge,3)
        if row<576:
            if step==0:
                s['ingress']=dict(row=row,physical_shard=((row%256)//2)//64)
                s['writes']=[dict(kind='rom',port=0,address=398720+row,data=row+1)]
                s['post_VM']={str(398720+row):row+1}
            elif step==1:
                c=dict(rank=0,generation=7,user=65536,xversion=52,pc=70,seq=3)
                s['reads']=[dict(src=0,address=398720+row,data=row+1,port=0,consumer_context=c)]
            else:s['credit_returns']=[row]
        if edge>=3 and (edge-3)%3==0 and (edge-3)//3<576:
            s['X_tags']=[dict(valid=True,fault=False,rank=0,generation=7,user=65536,xversion=52,pc=70,seq=3)]
        samples.append(s)
    return lease,samples


def test_all576_slot0_not_native_root_port_phase_lease():
    l,s=fixture();m=M.check(l,s,2)
    assert m['rows']==576 and not m['actual_current_program_enrolled']


@pytest.mark.parametrize('fault',['intervening_equal_write','original_root_writer','sameedge_read','early_release','sparse','tag_missing','stale_tag','alias','missing_family','early_credit'])
def test_phase_exclusion_and_consumer_fence(fault):
    l,s=fixture()
    if fault=='intervening_equal_write':s[2]['writes']=[dict(kind='xs_vm',port=0,address=398720,data=1)]
    if fault=='original_root_writer':s[3]['writes'].append(dict(kind='rom',port=1,address=398721,data=2))
    if fault=='sameedge_read':s[0]['reads']=s[1]['reads'];s[1]['reads']=[]
    if fault=='early_release':l['release_edge']=1728;s=s[:1729]
    if fault=='sparse':s.pop(2)
    if fault=='tag_missing':s[3]['X_tags']=[]
    if fault=='stale_tag':s[3]['X_tags'][0]['user']=0
    if fault=='alias':s[0]['writes'][0]['address']+=2**19
    if fault=='missing_family':s[2]['sampled_writer_classes']=list(M.V.WRITERS[:-1])
    if fault=='early_credit':s[1]['credit_returns']=[0]
    with pytest.raises(ValueError):M.check(l,s,2)


def test_no_source_implementation_or_deadline_invented():
    m=M.source_plan()
    assert m['port0_is_intercepted_ingress_not_native_root_id']
    assert not m['implemented_copied_ingress'] and not m['RTL_GO']
    assert m['actual_consumer_deadline'] is None


@pytest.mark.parametrize('fault',['wrong_operand','wrong_phase','wrong_frame','missing_external_block','bool_shard'])
def test_source_owned_endpoint_details(fault):
    l,s=fixture()
    if fault=='wrong_operand':s[1]['reads'][0]['port']=2
    if fault=='wrong_phase':l['context']['phase']=11
    if fault=='wrong_frame':l['descriptor']['obase']+=10000
    if fault=='missing_external_block':s[2]['writes']=[dict(kind='xa',port=0,address=10,data=0)]
    if fault=='bool_shard':s[0]['ingress']['physical_shard']=False
    with pytest.raises(ValueError):M.check(l,s,2)
