#!/usr/bin/env python3
"""Fail-closed additive CDC/domain/epoch successor of immutable R3.

The source-port-bound control channel is explicitly a directed verifier. Actual
production reversal needs installed clock/reset/drain provenance, still absent.
No RF ACK identity fields or physical clock qualification are fabricated.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/h3_complete_native_calendar_20261002/causal_domain_guard_r5'
R3_PIN='c3c0e800dbd6ea09a7fc35d1a2643244c19016de54bc6d4067e598d7a3731844'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(row):return json.dumps(row,sort_keys=True,separators=(',',':')).encode()
def parent_module():
    path=ROOT/'tools/h3_complete_native_calendar_owner_join_r3.py'
    if sha(path.read_bytes())!=R3_PIN:raise ValueError('immutable R3 source pin')
    name='causal_domains_r5_parent_'+sha(str(ROOT).encode())[:16]
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
        sys.modules[name]=m
        try:spec.loader.exec_module(m)
        except BaseException:del sys.modules[name];raise
    return sys.modules[name]
PARENT=parent_module()

class DomainBoundProductionOwnerJoin(PARENT.ProductionOwnerJoin):
    def __init__(self):
        super().__init__();self.initialize_domain_guards()
    def initialize_domain_guards(self):
        raw=(ROOT/OUT/'control_channel.json').read_bytes();self.control=json.loads(raw)
        source=(ROOT/OUT/self.control['source_path']).read_bytes()
        if sha(source)!=self.control['source_sha256']or b'wire arst=wrn&&rrn;'not in source:raise ValueError('source clock/reset port binding')
        required={'sender_domain':'CORE','sender_clock_port':'wc','sender_reset_port':'wrn',
                  'receiver_domain':'H1_streaming','receiver_clock_port':'rc','receiver_reset_port':'rrn',
                  'module':'ot_hbm_r14_fifo2','common_reset_expression':'wrn&&rrn','production_installed':False}
        if any(self.control.get(k)!=v for k,v in required.items()):raise ValueError('directed source port roles changed')
        self.contract_sha256=sha(raw);self.domain_epochs={'CORE':0,'H1_streaming':0}
        self.consumers={};self.channels={};self.sends={};self.receives={};self.invalidated=set()
    def consumer(self,*,die,SM,token,edge):
        super().consumer(die=die,SM=SM,token=token,edge=edge)
        event=dict(id='consumer:'+token,token=token,domain='H1_streaming',epoch=self.domain_epochs['H1_streaming'],edge=edge)
        self.consumers[token]=event
    def bind_control_channel(self,*,die,SM,token):
        x=self._owner((die,SM),token)
        if x['origin']!='directed_verifier_control':raise ValueError('production clock/reset/cohort source connection UNKNOWN')
        if token in self.channels or token in self.invalidated:raise ValueError('channel cannot rebind old accepted owner')
        self.channels[token]=dict(channel_id='source_control_reverse:'+token,
            binding_sha256=self.contract_sha256,source_sha256=self.control['source_sha256'],
            sender_domain='CORE',receiver_domain='H1_streaming',
            sender_epoch=self.domain_epochs['CORE'],receiver_epoch=self.domain_epochs['H1_streaming'],
            scope='directed_verifier_control_only')
    def _channel(self,token):
        c=self.channels.get(token)
        if c is None or token in self.invalidated:raise ValueError('bound current channel/reset cohort required')
        if (c['sender_epoch']!=self.domain_epochs[c['sender_domain']]
                or c['receiver_epoch']!=self.domain_epochs[c['receiver_domain']]):raise ValueError('stale channel reset epoch')
        return c
    def observe_reverse_send(self,*,token,domain,epoch,edge,consumer_event):
        c=self._channel(token);p=self.consumers.get(token)
        if (p is None or consumer_event!=p['id'] or token in self.sends
                or domain!=c['sender_domain']or type(epoch)is not int or epoch!=c['sender_epoch']
                or type(edge)is not int or edge<0):raise ValueError('source-ordered sender domain/epoch/consumer dependency')
        self.sends[token]=dict(id='reverse_send:'+token,token=token,domain=domain,epoch=epoch,edge=edge,depends_on=[consumer_event])
    def observe_reverse_receive(self,*,token,domain,epoch,edge,send_event):
        c=self._channel(token);send=self.sends.get(token);consumer=self.consumers.get(token)
        if (send is None or send_event!=send['id']or token in self.receives
                or domain!=c['receiver_domain']or type(epoch)is not int or epoch!=c['receiver_epoch']
                or type(edge)is not int or edge<0 or edge<consumer['edge']):raise ValueError('source-ordered receiver domain/epoch/send dependency')
        # Numeric edges are compared only within H1_streaming. Across domains
        # causality is an explicit accepted send->receive edge, not edge<edge.
        self.receives[token]=dict(id='reverse_receive:'+token,token=token,domain=domain,epoch=epoch,edge=edge,depends_on=[send_event])
    def reverse_receipt(self,token):
        c=self._channel(token);s=self.sends.get(token);r=self.receives.get(token)
        if s is None or r is None:raise ValueError('observed send/receive causality required')
        return dict(token=token,channel_id=c['channel_id'],channel_binding_sha256=c['binding_sha256'],
            source_sha256=c['source_sha256'],sender_domain=s['domain'],sender_edge=s['edge'],sender_epoch=s['epoch'],
            receiver_domain=r['domain'],receiver_edge=r['edge'],receiver_epoch=r['epoch'],
            send_event=s['id'],receive_event=r['id'],causal_events_sha256=sha(canonical([self.consumers[token],s,r])))
    def reverse(self,*,die,SM,token,edge,CDC_receipt,drain_pins=None):
        x=self._owner((die,SM),token)
        if x['origin']!='directed_verifier_control':raise ValueError('production channel/reset/drain proof UNKNOWN; owner retained')
        expected=self.reverse_receipt(token)
        if not isinstance(CDC_receipt,dict)or canonical(CDC_receipt)!=canonical(expected) or CDC_receipt['receiver_edge']!=edge:
            raise ValueError('exact source-bound domains/epochs/causal receipt required; owner retained')
        legacy={k:CDC_receipt[k]for k in ('token','sender_domain','sender_edge','receiver_domain','receiver_edge')}
        super().reverse(die=die,SM=SM,token=token,edge=edge,CDC_receipt=legacy,drain_pins=drain_pins)
    def observe_reset(self,*,domain,new_epoch):
        if domain not in self.domain_epochs or type(new_epoch)is not int or new_epoch<=self.domain_epochs[domain]:raise ValueError('source reset epoch must advance bound domain')
        self.domain_epochs[domain]=new_epoch
        self.invalidated.update(self.channels)
        # No lease, parent, RF SRAM, pending source ACK or hardware credit is
        # released on a software epoch change. Actual cancellation/drain missing.

def run_guard_control():
    # Explicit pinned directed fixture only: this is not production numerical
    # execution, an arithmetic oracle, or a measured/qualified endpoint trace.
    path=ROOT/'tests/test_h3_complete_native_calendar_owner_join_r3.py'
    if sha(path.read_bytes())!='9a88b76eec960e632c43ef080dc9af5a8b44d174d3f0c46cf944a25c3f41943b':raise ValueError('immutable R3 control fixture pin')
    spec=importlib.util.spec_from_file_location('domain_guard_private_fixture',path)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    def ready(guard):
        t=old.OwnerJoinTests();t.setUp()
        if guard:t.join.__class__=DomainBoundProductionOwnerJoin;t.join.initialize_domain_guards()
        t.ACK(read_data=bytes(range(256))*4)
        merged=t.join.merge(**t.key,token=t.token,payload=b'\x01'*t.command['active_words']*4)
        t.ACK();t.ACK(read_data=merged*2)
        t.join.visibility(**t.key,token=t.token,edge=t.edge);t.edge+=1
        t.join.consumer(**t.key,token=t.token,edge=t.edge);t.edge+=1
        return t
    def retire(t,receipt):
        t.join.reverse(**t.key,token=t.token,edge=t.edge,CDC_receipt=receipt,drain_pins=PARENT.directed_idle_pins(t.join.atomic))
    previous=ready(False)
    bad=dict(token=previous.token,sender_domain='NOT_A_BOUND_CLOCK_DOMAIN',sender_edge=17,receiver_domain='H1_streaming',receiver_edge=previous.edge)
    retire(previous,bad)
    historical=dict(verdict='FAIL_UNBOUND_DOMAIN_ACCEPTED',receipt=bad,live_owners=previous.join.summary()['live_SM_owners'],retired=previous.token in previous.join.retired_tokens)
    t=ready(True);j=t.join;j.bind_control_channel(**t.key,token=t.token)
    j.observe_reverse_send(token=t.token,domain='CORE',epoch=0,edge=100,consumer_event=j.consumers[t.token]['id'])
    j.observe_reverse_receive(token=t.token,domain='H1_streaming',epoch=0,edge=t.edge,send_event=j.sends[t.token]['id'])
    receipt=j.reverse_receipt(t.token);bad=dict(receipt,sender_domain='NOT_A_BOUND_CLOCK_DOMAIN')
    try:retire(t,bad)
    except ValueError as error:rejected=str(error)
    else:raise ValueError('successor must reject unknown sender before retirement')
    if t.token in j.retired_tokens or len(j.live)!=1:raise ValueError('reject cannot alter retained source owner')
    retire(t,receipt)
    return dict(schema='DOMAIN_EPOCH_CAUSAL_FAIL_CLOSED_SUCCESSOR_R5',W1_owner='Euclid',
        immutable_R3_pin=R3_PIN,immutable_R3_fixture_pin=sha(path.read_bytes()),
        preserved_historical_failure=historical,
        mutant_successor_rejection=rejected,mutant_rejection_left_owner_live=True,
        positive_directed_receipt=receipt,positive_directed_retired=True,
        source_channel=j.control,source_channel_sha256=j.contract_sha256,
        production_clock_reset_cohort_drain_bound=False,endpoint_trace_can_use_control_channel=False,
        actual_RF_ACK_fields=['valid','ready'],software_token_is_not_physical_ACK_identity=True,
        RF_sole_outstanding_plus_all_stale_copy_drain_proved=False,
        actual_Qwen_publication_order='bitmap before metadata under writer lock;87ca requirement stale, no source reorder',
        source_FIFO_ports_are_not_installed_clock_net_proof=True,
        physical_clock_or_SS_FF_credit=False,production_calls_closed=0,whole_token_ns=None)


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    raw=json.dumps(run_guard_control(),sort_keys=True,indent=2).encode()+b'\n';path=ROOT/OUT/'guard_control.json'
    if args.verify:
        if path.read_bytes()!=raw:raise ValueError('domain guard control replay changed')
    else:
        if path.exists()and path.read_bytes()!=raw:raise ValueError('historical verdict overwrite refused')
        path.write_bytes(raw)
    print('PASS bound directed domains/epochs/causality; historical mutant retained; production channel/reset/drain UNKNOWN')
if __name__=='__main__':main()
