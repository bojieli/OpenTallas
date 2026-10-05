import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h4_c0_pc40_workspace_lease_r1 as W

class PortLeaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet=W.V.verification_adapter().bind_eligible(40,0,generation=1,owner_tag=1,response_stall_bound=1)
    def lease(self):return W.WorkspaceLease(self.packet,enabled=True)
    def write(self,l,slot,raw):
        l.write_offer(slot,raw,l.leases[slot]);l.write_accept(wr_ready=True,ack_valid_before=False)
        l.common_ACK(l.owner,ack_valid=True,ack_ready=True)
    def inputs(self,l):
        self.write(l,17,b'a'*512);self.write(l,18,b'b'*512)
    def captured(self,l):
        self.inputs(l);l.read_offer((17,18));l.read_accept(rd_ready=True)
        l.response_capture(l.owner,rsp_valid=True,rsp_ready=True,payloads=[b'a'*512,b'b'*512])
        l.native_complete(l.owner,output_sha256=W.sha(b'c'*512))
    def test_default_off(self):
        with self.assertRaisesRegex(ValueError,'default off'):W.WorkspaceLease(self.packet)
    def test_source_RF_common_ACK_and_widths(self):
        m=W.model();self.assertEqual(m['source_ports']['ACK_tag_bits'],0)
        self.assertEqual(m['source_ports']['wr_data_bits'],4096)
        self.assertEqual(m['source_ports']['rsp_b_bits'],4096)
        self.assertFalse(m['installed_call_admitted'])
        self.assertEqual(m['source_native_service']['serialized_service_ticks'],14)
    def test_actual_caller_up_home_and_finite_NoC_debit(self):
        m=W.caller_preparation_model()
        self.assertEqual((m['source_up_home']['storage_SM'],m['source_up_home']['RFslot9']),(24,32))
        self.assertEqual(m['source_up_home']['word_start'],6144)
        self.assertEqual(m['NoC_up_payload_bits'],4096)
        self.assertEqual(m['source_RF_read_services'],2)
        self.assertFalse(m['NoC_idealized'])
        self.assertIsNone(m['caller_retained_slot_binding'])
    def test_early_ACK_rejected(self):
        l=self.lease()
        with self.assertRaises(ValueError):l.common_ACK(l.owner,ack_valid=True,ack_ready=True)
    def test_source_ACK_lane_must_be_idle_before_accept(self):
        l=self.lease();l.write_offer(17,b'a'*512,l.leases[17])
        with self.assertRaises(ValueError):l.write_accept(wr_ready=True,ack_valid_before=True)
    def test_single_write_no_alias_before_ACK(self):
        l=self.lease();l.write_offer(17,b'a'*512,l.leases[17])
        with self.assertRaises(ValueError):l.write_offer(18,b'b'*512,l.leases[18])
    def test_wrong_owner_ACK(self):
        l=self.lease();l.write_offer(17,b'a'*512,l.leases[17]);l.write_accept(wr_ready=True,ack_valid_before=False)
        with self.assertRaises(ValueError):l.common_ACK((0,0,2,1),ack_valid=True,ack_ready=True)
    def test_wrong_lease_and_width(self):
        l=self.lease()
        with self.assertRaises(ValueError):l.write_offer(17,b'a'*512,'stale')
        with self.assertRaises(ValueError):l.write_offer(17,b'a'*256,l.leases[17])
    def test_frame_packing_banks(self):
        f=W.frame(bytes(range(256))*2,version='actual',lease='lease',slot=145,role='source')
        self.assertEqual(len(f['RF_banks']),16);self.assertEqual(f['RF_banks'][0]['page'],1)
        self.assertEqual(f['RF_banks'][0]['row'],17)
        self.assertEqual(f['RF_banks'][-1]['source_byte_range'],[480,512]);self.assertIsNone(f['parent55'])
    def test_changed_captured_payload_rejected(self):
        p=self.packet;c=p['native_command'];homes=c['source_version_home_refs']+[c['destination_version_home_ref']]
        frames={h['RF_vectors'][0]:W.frame(bytes(512),version=h['version'],lease=h['lease'],slot=h['RF_vectors'][0],role='fixture') for h in homes}
        l=W.WorkspaceLease(p,enabled=True,frame_bindings=frames)
        with self.assertRaisesRegex(ValueError,'captured source'):l.write_offer(17,b'x'*512,l.leases[17])
    def test_wrong_RF_response_order(self):
        l=self.lease();self.inputs(l);l.read_offer((17,18));l.read_accept(rd_ready=True)
        with self.assertRaises(ValueError):l.response_capture(l.owner,rsp_valid=True,rsp_ready=True,payloads=[b'b'*512,b'a'*512])
    def test_input_alias_not_released_after_capture(self):
        l=self.lease();self.captured(l)
        with self.assertRaises(ValueError):l.write_offer(18,b'c'*512,l.leases[18])
    def test_reuse_requires_output_ACK_consumer_reverse(self):
        l=self.lease();self.captured(l)
        with self.assertRaises(ValueError):l.retire()
        l.write_offer(19,b'c'*512,l.leases[19]);l.write_accept(wr_ready=True,ack_valid_before=False)
        with self.assertRaises(ValueError):l.consumer_accept(l.owner)
        l.common_ACK(l.owner,ack_valid=True,ack_ready=True);l.consumer_accept(l.owner)
        with self.assertRaises(ValueError):l.retire()
        l.validated_reverse(l.owner,source_event='validated_reverse_grant',sequence=l.sequence+1)
        l.retire();self.assertTrue(l.released)
        self.assertFalse(l.log[-1]['source_gate_home_released'])
    def test_stale_reverse_sequence(self):
        l=self.lease();self.captured(l);self.write(l,19,b'c'*512);l.consumer_accept(l.owner)
        with self.assertRaises(ValueError):l.validated_reverse(l.owner,source_event='validated_reverse_grant',sequence=0)
    def test_source_packet_width_tamper(self):
        p=copy.deepcopy(self.packet);p['native_command']['source_bittypes'][0]=64
        with self.assertRaises(ValueError):W.WorkspaceLease(p,enabled=True)

if __name__=='__main__':unittest.main()
