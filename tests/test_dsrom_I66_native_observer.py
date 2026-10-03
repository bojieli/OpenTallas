import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_I66_native_observer as M


def witness():
    c=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=8,user=0xf1234567,xversion=7,pc=66)
    publications=[dict(context=copy.deepcopy(c),row=r,postNBA_edge=30+r//128,address=398720+r,
                       value=0x12345678,physical_shard=((r%256)//2)//64) for r in range(576)]
    credits=[dict(context=copy.deepcopy(c),row=r,postNBA_edge=35+r//128,
                  physical_shard=((r%256)//2)//64) for r in range(576)]
    packet=dict(context=copy.deepcopy(c),outstanding_after=0,
                accepted_packets=[dict(id=3,edge=22),dict(id=4,edge=23)],
                captured_ACKs=[dict(id=3,postNBA_edge=38),dict(id=4,postNBA_edge=39)])
    f=dict(context=copy.deepcopy(c),edge=40,adapter_st=5,s_go=0,native_idle=1,
           phase_active=1,qualified_retired=1,effective_idle=1,healthy_reset_epoch=1,
           adapter_fault=0,spine_fault=0)
    issue=dict(context=copy.deepcopy(c),edge=41,registered_accept_edge=42,pc=67,
               waited=1,unit_ready=1,q_gate=1,kv_gate=1,m0_gate=1,healthy_reset_epoch=1,d_skip=0)
    read=dict(context=copy.deepcopy(c),edge=70,observed_tag_edge=72,address=398720,
              source_seq=19,observed_tag_seq=19)
    return [c,publications,credits,packet,f,issue,read]


def test_complete_concrete_join_preserves_fulluser_and_does_not_claim_actual():
    w=witness(); old=copy.deepcopy(w); r=M.retirement_join(*w)
    assert w==old and r['F']==40 and r['last_VM_visible']==34 and r['last_credit']==39
    assert not r['actual_current_enrollment'] and not r['physical_deadline_proved']
    assert r['absolute_service_bound'] is None


@pytest.mark.parametrize('fault',['missingpub','missingcredit','dup','shard','alias','boolvalue','floatcredit',
    'sameedgecredit','sameedgeF','busyACK','missingACK','dupACK','sameedgeACK','stalecredit','highuseralias',
    'Fidle','Fgo','Fnative','Freset','Fbool','wronglaterW2','falsegate','skip','earlyissue','lateNBA',
    'sameedgeread','tagmissing','tagstale','readalias','adapterfault','spinefault'])
def test_adversarial_retirement_and_source_lineage_reject_before_mutation(fault):
    w=witness();c,p,credits,packet,f,issue,read=w
    if fault=='missingpub':p.pop()
    elif fault=='missingcredit':credits.pop()
    elif fault=='dup':p[-1]['row']=0
    elif fault=='shard':p[0]['physical_shard']=1
    elif fault=='alias':p[0]['address']+=1<<19
    elif fault=='boolvalue':p[0]['value']=True
    elif fault=='floatcredit':credits[0]['postNBA_edge']=35.0
    elif fault=='sameedgecredit':credits[0]['postNBA_edge']=p[0]['postNBA_edge']
    elif fault=='sameedgeF':credits[0]['postNBA_edge']=40
    elif fault=='busyACK':packet['outstanding_after']=1
    elif fault=='missingACK':packet['captured_ACKs'].pop()
    elif fault=='dupACK':packet['captured_ACKs'].append(copy.deepcopy(packet['captured_ACKs'][0]))
    elif fault=='sameedgeACK':packet['captured_ACKs'][0]['postNBA_edge']=22
    elif fault=='stalecredit':credits[0]['context']['generation']+=1
    elif fault=='highuseralias':credits[0]['context']['user']&=0xffff
    elif fault=='Fidle':f['adapter_st']=0
    elif fault=='Fgo':f['s_go']=1
    elif fault=='Fnative':f['native_idle']=0
    elif fault=='Freset':f['healthy_reset_epoch']=0
    elif fault=='Fbool':f['qualified_retired']=True
    elif fault=='wronglaterW2':issue['pc']=79
    elif fault=='falsegate':issue['kv_gate']=0
    elif fault=='skip':issue['d_skip']=1
    elif fault=='earlyissue':issue['edge']=40;issue['registered_accept_edge']=41
    elif fault=='lateNBA':issue['registered_accept_edge']=43
    elif fault=='sameedgeread':read['edge']=34;read['observed_tag_edge']=36
    elif fault=='tagmissing':read['observed_tag_edge']=71
    elif fault=='tagstale':read['observed_tag_seq']+=1
    elif fault=='readalias':read['address']+=1<<19
    elif fault=='adapterfault':f['adapter_fault']=1
    elif fault=='spinefault':f['spine_fault']=1
    old=copy.deepcopy(w)
    with pytest.raises(ValueError):M.retirement_join(*w)
    assert w==old


def test_generated_disabled_inverse_and_no_engine_drives():
    text=M.generate();r=M.inverse(text)
    assert r==M.sha((M.INPUT/'runtime_wrapper.sv.txt').read_bytes())
    body=text[text.index(M.BEGIN):text.index(M.END)]
    assert 'parameter integer I66_OBSERVE = 0' in text
    assert 'generate if (I66_OBSERVE != 0)' in body
    assert '$strobe' in body and 'saved_addr[18:0]' in body and 'address=%h' in body
    assert 'force ' not in body and 'dut.u_tile.vm[' in body
    assert all('writer_'+family in body for family in M.WRITERS)
    assert 'dut.u_tile.xs_rd_src[p*2 +: 2] == 0' in body
    # No clock, reset, eval, argv or protected statement is removed by translation.
    assert M.inverse(text)==r


def test_wrong_signal_or_disabled_engine_change_breaks_exact_inverse():
    text=M.generate()
    for bad in [text.replace('dut.u_tile.rom_we[r]','dut.rom_we[r]'),
                text.replace('.host_entry(14\'d0)', '.host_entry(14\'d66)')]:
        with pytest.raises(ValueError):M.inverse(bad)


def test_native_parse_preserves_actual_pre_post_and_unknown_provider():
    events=M.parse_native(['noise','I66HOOK pre 3 0 edge pc=42 writer_mask=001',
        'I66HOOK pre 3 0 writer_rom rom_we=1 rom_waddr=61600 rom_wdata=3f800000',
        'I66HOOK post 3 0 VM root=0 address=61600 value=3f800000'])
    assert events[-1]['region']=='post' and events[-1]['fields']['value']==0x3f800000
    assert 'context' not in events[-1] and 'credit' not in events[-1]


@pytest.mark.parametrize('line',['I66HOOK post 3 0 edge pc=0','I66HOOK pre 3 0 VM address=0',
    'I66HOOK pre -1 0 read port=0','I66HOOK pre 3 4 edge pc=0',
    'I66HOOK pre 3 0 edge pc=x','I66HOOK pre 3 0 edge pc=0 pc=1',
    'I66HOOK pre 3 0 credit row=0'])
def test_malformed_or_fabricated_native_callbacks_rejected(line):
    with pytest.raises(ValueError):M.parse_native([line])


def test_model_no_native_or_physical_admission_and_exact_observer_state():
    r=M.model()
    assert r['observer_state_bits']==12096 and r['observer_state_bytes']==1512
    assert not r['elaboration_pass'] and not r['selected_candidate_run_ready']
    assert r['earliest_run']['binary'] is None and not r['earliest_run']['launch_ready']
    assert r['absolute_service_deadline'] is None and r['jobs_launched']==0
    assert r['C'] is None and r['physical_stations'] is None
