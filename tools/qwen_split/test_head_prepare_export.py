import copy
import unittest
from head_prepare_age import export_result

class ActualHostScheduleCaller(unittest.TestCase):
    def setUp(self):
        # The source/core intervals and descriptor edge9 are the actual bound
        # HOST path coupon; GEN hashes are fixture identities, never production.
        self.result=dict(die_sha256='fixture-gen-not-production',filler_head_prepare_edges=14,user0_prepare_only_min_edges=15,
                         actual_transport_edges={'SF.head_descriptor':2},source_intrinsic_edges=dict(face_input_capture=1,face_held_bank=1))
        self.profile=dict(schema='opentallas.qwen.head_prepare_component_schedule.v1',scope='COMPONENT_ONLY',die_sha256=self.result['die_sha256'],
                          native_prepare_capture_edge=2,token=304,position=203,filler_descriptor_edges=[],reserved_held_bank_edge=13,
                          host_core_interval=dict(first_core_edge=8,last_core_edge=10,interval_basis='post_edge_publication',
                              tag=(420<<43)|(304<<19)|(203<<6),epoch=420,generation=1,fused_capability=True))
    def test_missing_profile_cannot_emit_universal_scalar(self):
        r,code=export_result(self.result)
        self.assertEqual(code,2);self.assertIsNone(r['head_prepare_edges']);self.assertFalse(r['calendar_installable'])
    def test_explicit_component_caller_accepts_actual_interval(self):
        r,code=export_result(self.result,component_only=True,host_schedule=self.profile)
        self.assertEqual(code,0);self.assertEqual(r['host_schedule_component']['native_join']['descriptor_core_edge'],9)
        self.assertEqual(r['host_schedule_component']['held_bank_ready_edge'],13)
        self.assertFalse(r['calendar_installable']);self.assertIsNone(r['head_prepare_edges'])
    def test_component_receipt_cannot_qualify_production(self):
        r,code=export_result(self.result,host_schedule=self.profile)
        self.assertEqual(code,2);self.assertFalse(r['calendar_installable'])
    def test_wrong_identity_control(self):
        self.profile['host_core_interval']['tag']^=1<<19
        with self.assertRaises(ValueError):export_result(self.result,component_only=True,host_schedule=self.profile)
    def test_early_reservation_control(self):
        self.profile['reserved_held_bank_edge']=12
        with self.assertRaises(ValueError):export_result(self.result,component_only=True,host_schedule=self.profile)
    def test_wrong_gen_control(self):
        self.profile['die_sha256']='different-gen'
        with self.assertRaises(ValueError):export_result(self.result,component_only=True,host_schedule=self.profile)
    def test_early_host_pulse_control(self):
        self.profile['host_core_interval'].update(first_core_edge=0,last_core_edge=2)
        with self.assertRaises(ValueError):export_result(self.result,component_only=True,host_schedule=self.profile)

if __name__=='__main__':unittest.main()
