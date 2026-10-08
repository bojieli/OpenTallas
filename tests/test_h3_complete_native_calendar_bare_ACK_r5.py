import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bare_ACK_r5_tests',ROOT/'tools/h3_complete_native_calendar_bare_ACK_r5.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class SourceACKTests(unittest.TestCase):
    def setUp(self):
        self.rf=m.RFService();self.owner=m.SoleACKContext(self.rf)
        self.context=dict(version='directed',provider_ref='directed_RF',lease='control1',generation=0,SM=0,RF_slot=7)
        self.payload=bytes(range(256))*2
    def test_common_ACK_is_untagged_and_both_copies_share_write_go(self):
        e=self.owner.accept_write(self.context,address=7,payload=self.payload)
        self.assertEqual(len(e['both_copy_bank_write_go']),32)
        self.assertEqual(e['ACK_wire_fields'],['valid','ready'])
        self.assertEqual(self.rf.memory[0][7],self.rf.memory[1][7])
        for _ in range(3):
            blocked=self.rf.tick(rd_valid=True,wr_valid=True,wr_addr=8,wr_data=self.payload)
            self.assertFalse(blocked['read_go']);self.assertFalse(blocked['write_go'])
        receipt=self.owner.capture_common_ACK();self.assertEqual(receipt['retained_context'],self.context)
        self.assertNotIn('tag',receipt['wire_ACK'])
    def test_wrong_owner_and_double_accept_or_completion_rejected(self):
        self.owner.accept_write(self.context,address=7,payload=self.payload)
        with self.assertRaises(ValueError):self.owner.accept_write(dict(self.context,generation=1),address=7,payload=self.payload)
        self.owner.capture_common_ACK()
        with self.assertRaises(ValueError):self.owner.capture_common_ACK()
        with self.assertRaises(ValueError):self.owner.consumer_reverse(dict(self.context,generation=1))
        self.owner.consumer_reverse(self.context)
    def test_reset_preserves_SRAM_and_requires_all_actual_copy_paths(self):
        self.owner.accept_write(self.context,address=7,payload=self.payload)
        self.owner.begin_reset(old_copy_paths=['RF_local','actual_return_FIFO','accepted_owner'])
        self.owner.coordinated_local_cancel()
        self.assertEqual(self.rf.memory[0][7],self.payload)
        with self.assertRaises(ValueError):self.owner.resume()
        self.owner.observe_drained('RF_local',admission_blocked=True,live_copies=0)
        with self.assertRaises(ValueError):self.owner.resume()
        with self.assertRaises(ValueError):self.owner.observe_drained('actual_return_FIFO',admission_blocked=True,live_copies=1)
        for path in ('actual_return_FIFO','accepted_owner'):self.owner.observe_drained(path,admission_blocked=True,live_copies=0)
        self.owner.resume();self.assertIsNotNone(self.owner.accept_write(dict(self.context,generation=1),address=7,payload=self.payload))
    def test_uninitialized_reads_never_get_zero_or_golden_payload(self):
        self.rf.tick(rd_valid=True,rd_a=7,rd_b=8)
        with self.assertRaisesRegex(ValueError,'uninitialized'):self.rf.tick()
    def test_read_pipeline_and_competing_source_ports(self):
        for a in (7,8):self.rf.tick(wr_valid=True,wr_addr=a,wr_data=self.payload);self.rf.tick(ack_ready=True)
        e=self.rf.tick(rd_valid=True,rd_a=7,rd_b=8,wr_valid=True,wr_addr=9,wr_data=self.payload)
        self.assertTrue(e['read_go']);self.assertFalse(e['write_go'])
        self.rf.tick();self.assertEqual(self.rf.response,self.payload*2)
        self.assertFalse(self.rf.tick(wr_valid=True,wr_addr=9,wr_data=self.payload)['write_go'])
        self.rf.tick(rsp_ready=True)
        self.assertTrue(self.rf.tick(rd_valid=True,wr_valid=True,wr_addr=9,wr_data=self.payload)['write_go'])
    def test_reachable_partial_reset_stalls_not_epoch_credit(self):
        result=m.derive();self.assertEqual([w['reset']for w in result['partial_reset_witnesses']],['RF_only','fence_only'])
        self.assertEqual(result['W1_owner'],'Euclid')
        self.assertFalse(result['reset_contract']['RF_reset_alone_proves_remote_drain'])
        self.assertIsNone(result['reset_contract']['fourbit_generation_wrap_safety'])
        self.assertEqual(result['production_calls_closed'],0)
    def test_actual_selected_command_context_requires_matching_lease(self):
        _,src=m.inputs();c=json.loads(src['commands.json.gz'])['RMW'][0]
        digest=m.sha(json.dumps(c,sort_keys=True,separators=(',',':')).encode())
        lease=dict(source_command_sha256=digest,provider_reference=c['provider_reference'],lease='directed_receipt_only')
        ctx=m.source_RF_context(c['id'],lease_receipt=lease)
        self.assertEqual((ctx['SM'],ctx['RF_slot'],ctx['die']),(c['SM'],c['RF_slot'],c['die']))
        with self.assertRaises(ValueError):m.source_RF_context(c['id'],lease_receipt=dict(lease,provider_reference=-1))
        with self.assertRaises(ValueError):m.source_RF_context(c['id'],lease_receipt=None)

class HeldRouteTests(unittest.TestCase):
    def test_actual_route_II40_no_same_edge_reaccept(self):
        result=m.derive();self.assertEqual(result['route']['accept_FAST_edge_ordinals'],[0,40,80,120])
        self.assertEqual(result['route']['consume_FAST_edge_ordinals'],[39,79,119])
        self.assertEqual(result['route']['aggregate128PC_sector32_Bpc_upper'],102.4)
    def test_backpressure_retains_packet_and_owner(self):
        route=m.HeldRoute();route.tick(iv=True,packet=b'old')
        for _ in range(50):self.assertFalse(route.tick(iv=True,packet=b'new')['accepted'])
        self.assertEqual(route.packet,b'old');self.assertTrue(route.tick(ore=True)['consumed'])
        self.assertTrue(route.tick(iv=True,packet=b'new')['accepted'])

if __name__=='__main__':unittest.main()
