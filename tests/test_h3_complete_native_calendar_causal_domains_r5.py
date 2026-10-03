import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('causal_r5_tests','tools/h3_complete_native_calendar_causal_domains_r5.py')
old=load('causal_r5_old_fixture','tests/test_h3_complete_native_calendar_owner_join_r3.py')
def ready(guard=True):
    t=old.OwnerJoinTests();t.setUp()
    if guard:
        t.join.__class__=m.DomainBoundProductionOwnerJoin;t.join.initialize_domain_guards()
    t.ACK(read_data=bytes(range(256))*4)
    merged=t.join.merge(**t.key,token=t.token,payload=b'\x01'*t.command['active_words']*4)
    t.ACK();t.ACK(read_data=merged*2)
    t.join.visibility(**t.key,token=t.token,edge=t.edge);t.edge+=1
    t.join.consumer(**t.key,token=t.token,edge=t.edge);t.edge+=1
    return t
def bind(t):
    j=t.join;j.bind_control_channel(**t.key,token=t.token)
    j.observe_reverse_send(token=t.token,domain='CORE',epoch=0,edge=100,consumer_event=j.consumers[t.token]['id'])
    j.observe_reverse_receive(token=t.token,domain='H1_streaming',epoch=0,edge=t.edge,send_event=j.sends[t.token]['id'])
    return j.reverse_receipt(t.token)
def retire(t,receipt):t.join.reverse(**t.key,token=t.token,edge=t.edge,CDC_receipt=receipt,drain_pins=m.PARENT.directed_idle_pins(t.join.atomic))
class DomainGuardTests(unittest.TestCase):
    def test_preserved_R3_mutant_accepts_unbound_sender(self):
        t=ready(False);retire(t,dict(token=t.token,sender_domain='NOT_A_BOUND_CLOCK_DOMAIN',sender_edge=17,receiver_domain='H1_streaming',receiver_edge=t.edge))
        self.assertEqual(t.join.summary()['live_SM_owners'],0)
    def test_positive_source_port_bound_control_retirement(self):
        t=ready();retire(t,bind(t));self.assertEqual(t.join.summary()['live_SM_owners'],0)
    def test_unknown_sender_receiver_epoch_causal_and_extra_field_reject(self):
        for field,value in [('sender_domain','NOT_A_BOUND_CLOCK_DOMAIN'),('receiver_domain','bad'),('sender_epoch',1),('sender_epoch',False),('receiver_epoch',1),('receiver_epoch',False),('source_sha256','0'*64),('causal_events_sha256','0'*64),('send_event','bad'),('extra','synthetic_ACK_tag')]:
            with self.subTest(field=field):
                t=ready();receipt=bind(t);receipt[field]=value
                with self.assertRaises(ValueError):retire(t,receipt)
                self.assertEqual(t.join.summary()['live_SM_owners'],1)
                self.assertNotIn(t.token,t.join.retired_tokens)
    def test_missing_channel_legacy_receipt_and_receive_before_send_reject(self):
        t=ready()
        with self.assertRaises(ValueError):retire(t,dict(token=t.token,sender_domain='CORE',sender_edge=17,receiver_domain='H1_streaming',receiver_edge=t.edge))
        t.join.bind_control_channel(**t.key,token=t.token)
        with self.assertRaises(ValueError):t.join.observe_reverse_receive(token=t.token,domain='H1_streaming',epoch=0,edge=t.edge,send_event='unobserved_send')
    def test_reset_invalidates_old_receipts_without_releasing_owner(self):
        for domain in ('CORE','H1_streaming'):
            t=ready();receipt=bind(t);t.join.observe_reset(domain=domain,new_epoch=1)
            with self.assertRaises(ValueError):retire(t,receipt)
            self.assertEqual(t.join.summary()['live_SM_owners'],1)
            with self.assertRaises(ValueError):t.join.bind_control_channel(**t.key,token=t.token)
    def test_receiver_before_source_consumer_rejects_without_cross_clock_comparison(self):
        t=ready();j=t.join;j.bind_control_channel(**t.key,token=t.token)
        j.observe_reverse_send(token=t.token,domain='CORE',epoch=0,edge=1000000,consumer_event=j.consumers[t.token]['id'])
        with self.assertRaises(ValueError):j.observe_reverse_receive(token=t.token,domain='H1_streaming',epoch=0,edge=0,send_event=j.sends[t.token]['id'])
        j.observe_reverse_receive(token=t.token,domain='H1_streaming',epoch=0,edge=t.edge,send_event=j.sends[t.token]['id'])
        retire(t,j.reverse_receipt(t.token))
    def test_endpoint_trace_cannot_use_control_binding(self):
        t=ready();t.join.live[t.key['die'],t.key['SM']]['origin']='endpoint_trace'
        with self.assertRaisesRegex(ValueError,'production'):t.join.bind_control_channel(**t.key,token=t.token)
        with self.assertRaisesRegex(ValueError,'production'):retire(t,{})
        self.assertEqual(t.join.summary()['live_SM_owners'],1)

if __name__=='__main__':unittest.main()
