#!/usr/bin/env python3
import copy, hashlib, importlib.util, json, subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path.cwd()
OUT=Path('/tmp/review-dewey-causal-r5')
p=ROOT/'tests/test_h3_complete_native_calendar_causal_domains_r5.py'
spec=importlib.util.spec_from_file_location('independent_r5_fixture',p)
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
rows=[]

def rejected_owner(t, thunk, name):
    before=t.join.summary()
    try: thunk()
    except ValueError as exc: reason=str(exc)
    else: raise AssertionError(name+' unexpectedly accepted')
    assert t.join.summary()==before, name+' changed owner state'
    assert t.token not in t.join.retired_tokens
    rows.append(dict(name=name,rejected_before_retire=True,owner_state_unchanged=True,reason=reason))

old=T.ready(False)
legacy=dict(token=old.token,sender_domain='NOT_A_BOUND_CLOCK_DOMAIN',sender_edge=17,receiver_domain='H1_streaming',receiver_edge=old.edge)
T.retire(old,legacy)
assert old.token in old.join.retired_tokens
historical=dict(sender_domain=legacy['sender_domain'],retired=True,live_SM_owners=old.join.summary()['live_SM_owners'])
for field,bad in [('sender_domain','NOT_A_BOUND_CLOCK_DOMAIN'),('sender_domain','H1_streaming'),
                  ('receiver_domain','CORE'),('sender_epoch',1),('receiver_epoch',1),
                  ('source_sha256','0'*64),('channel_binding_sha256','0'*64),('channel_id','foreign_channel'),
                  ('causal_events_sha256','0'*64),('receive_event','unobserved_receive'),
                  ('receiver_edge',-1),('extra','unbound_reset_proof')]:
    t=T.ready();r=T.bind(t);r[field]=bad
    rejected_owner(t,lambda:T.retire(t,r),field+':'+str(bad))
for domain in ('CORE','H1_streaming'):
    t=T.ready();r=T.bind(t);t.join.observe_reset(domain=domain,new_epoch=1)
    rejected_owner(t,lambda:T.retire(t,r),'old_receipt_after_'+domain+'_reset')
    rejected_owner(t,lambda:t.join.bind_control_channel(**t.key,token=t.token),'rebind_after_'+domain+'_reset')
t=T.ready();t.join.live[(t.key['die'],t.key['SM'])]['origin']='endpoint_trace'
rejected_owner(t,lambda:t.join.bind_control_channel(**t.key,token=t.token),'production_channel_binding_forbidden')
rejected_owner(t,lambda:T.retire(t,{}),'production_retirement_forbidden')
# Verify guard input roles/source bytes without writing any source/input file.
control_path=ROOT/T.m.OUT/'control_channel.json'
source_path=ROOT/T.m.OUT/'inputs/fifo2.sv'
read=Path.read_bytes
for field,bad in [('sender_domain','H1_streaming'),('receiver_domain','CORE'),
                  ('sender_clock_port','rc'),('receiver_reset_port','wrn'),
                  ('common_reset_expression','wrn||rrn'),('production_installed',True)]:
    altered=json.loads(read(control_path));altered[field]=bad
    blob=json.dumps(altered).encode()
    def reader(p): return blob if p==control_path else read(p)
    with patch.object(Path,'read_bytes',reader):
        try:T.m.DomainBoundProductionOwnerJoin()
        except ValueError as exc:reason=str(exc)
        else:raise AssertionError('source role mutant accepted '+field)
    rows.append(dict(name='control_source_role_'+field,rejected_before_owner_creation=True,reason=reason))
def changed(p): return read(p)+b'\n// source changed\n' if p==source_path else read(p)
with patch.object(Path,'read_bytes',changed):
    try:T.m.DomainBoundProductionOwnerJoin()
    except ValueError as exc:reason=str(exc)
    else:raise AssertionError('source hash mutation accepted')
rows.append(dict(name='source_bytes_pin',rejected_before_owner_creation=True,reason=reason))
# Domain-local edge zero-gap remains permitted; don't turn it into priced CDC.
t=T.ready();j=t.join;j.bind_control_channel(**t.key,token=t.token)
j.observe_reverse_send(token=t.token,domain='CORE',epoch=0,edge=1000000,consumer_event=j.consumers[t.token]['id'])
consumer_edge=j.consumers[t.token]['edge']
j.observe_reverse_receive(token=t.token,domain='H1_streaming',epoch=0,edge=consumer_edge,send_event=j.sends[t.token]['id'])
r=j.reverse_receipt(t.token)
positive_channel=dict(sender_domain=r['sender_domain'],receiver_domain=r['receiver_domain'],sender_epoch=r['sender_epoch'],receiver_epoch=r['receiver_epoch'],numeric_cross_domain_edges_compared=False,receive_equal_consumer_edge_accepted=True)
# Retire only at the exact receipt edge in the fixture.
t.edge=consumer_edge;T.retire(t,r);assert t.token in j.retired_tokens
with __import__('contextlib').redirect_stdout(__import__('io').StringIO()): replay=T.m.run_guard_control()
raw=(json.dumps(replay,sort_keys=True,indent=2)+'\n').encode()
assert raw==read(ROOT/T.m.OUT/'guard_control.json')
parent_raw=read(ROOT/'tools/h3_complete_native_calendar_owner_join_r3.py')
assert parent_raw==subprocess.check_output(['git','show','b8290b552:tools/h3_complete_native_calendar_owner_join_r3.py'])
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
main=subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','rev-parse','HEAD'],text=True).strip()
receipt=dict(status='PASS_DIRECTED_SOURCE_CONTROL_ONLY',reviewed_commit=head,current_main_snapshot=main,
 historical_R3_invalid_sender=historical,independent_negative_count=len(rows),independent_mutants=rows,
 allowed_pair=positive_channel,cold_guard_byte_exact=True,
 immutable_R3_byte_identical=True,
 source_pins={str(p.relative_to(ROOT)):hashlib.sha256(read(p)).hexdigest() for p in [ROOT/'tools/h3_complete_native_calendar_causal_domains_r5.py',ROOT/'tests/test_h3_complete_native_calendar_causal_domains_r5.py',ROOT/'tools/h3_complete_native_calendar_owner_join_r3.py',control_path,source_path]},
 guard='receipt exactly matches current source-bound CORE->H1_streaming directed channel, current reset epochs, observed consumer/send/receive dependencies; production origin rejected before retire',
 limitations=['source ports are archived FIFO declarations, not installed clock/reset wiring',
 'consumer/send/receive observations supplied by directed fixture, no production provenance',
 'receiver==consumer edge accepted: no positive-cycle transport/CDC cost inferred from software order',
 'sender and receiver numeric edges belong to different domains and are not compared',
 'R5 reset invalidates old channels without releasing owner; actual cancellation/drain not implemented',
 'original RF ACK remains bare valid/ready; owner token does not create physical tag',
 'source hash verifies supplied control-channel source; immutable review hashes must accompany intake'],
 production_fixture_credit=False,hardware_qualified=False,whole_token_rate=None,
 W6_dependency='separate prospective contract fc62c66ab; model/F0 still required before engine RTL')
(OUT/'independent_review.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print('PASS historical R3 accepted; R5 rejects-before-retire;',len(rows),'independent mutants; cold exact; production refused')
