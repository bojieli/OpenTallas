import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).resolve().parents[1]/'tools/model_dsrom_ckv_lease_integration.py'
S=importlib.util.spec_from_file_location('lease_model',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)


class IntegratedLeaseTests(unittest.TestCase):
    def loaded(self):
        x=M.Ownership();x.select(True,True)
        for r in range(512):x.receive(x.epoch,r,r,r,(r,17),r%4,r%4)
        return x
    def test_all512_both_retirements_nine_actual_completions(self):
        x=self.loaded()
        for r in range(512):
            x.reserve_broadcast(r)
            for dst in range(3):x.ack(x.epoch,r,dst)
        for i in range(9):self.assertEqual(x.pub.request(),i);x.pub.complete()
        for pv in (False,True):x.start(pv);x.emit_done();x.retire(True,True)
        x.close(True);self.assertFalse(x.active);self.assertEqual(len(x.rows),512)
    def test_request_accept_is_not_publication(self):
        p=M.Publication();p.request();self.assertFalse(p.done)
        with self.assertRaises(ValueError):p.request()
        p.complete()
        for i in range(1,8):p.request();p.complete()
        p.request();self.assertFalse(p.done);p.complete();self.assertTrue(p.done)
        with self.assertRaises(ValueError):p.complete()
    def test_stale_duplicate_wrong_owner_wrong_id_never_mutate(self):
        x=self.loaded();before=dict(x.rows)
        for e,r,g,expected,owner,eo in [(0,0,0,0,0,0),(x.epoch,0,0,0,0,0),(x.epoch,512,512,512,0,0),(x.epoch,1,2,1,0,0),(x.epoch,1,1,1,1,0)]:
            with self.assertRaises(ValueError):x.receive(e,r,g,expected,999,owner,eo)
            self.assertEqual(x.rows,before)
    def test_no_QK_only_or_premature_engine_reuse(self):
        x=self.loaded()
        with self.assertRaises(ValueError):x.start(True)
        x.start(False);x.emit_done()
        with self.assertRaises(ValueError):x.retire(True,False)
        with self.assertRaises(ValueError):x.start(True)
        x.retire(True,True)
        with self.assertRaises(ValueError):x.select(True,True)
        x.start(True)
        with self.assertRaises(ValueError):x.close(True)
    def test_stale_duplicate_ACK_not_credit(self):
        x=self.loaded();x.reserve_broadcast(7)
        pending=set(x.pending)
        with self.assertRaises(ValueError):x.ack(0,7,0)
        self.assertEqual(x.pending,pending)
        x.ack(x.epoch,7,0)
        with self.assertRaises(ValueError):x.ack(x.epoch,7,0)
        self.assertEqual(len(x.pending),2)
    def test_reset_and_wrap_require_actual_drain(self):
        x=M.Ownership();x.epoch=65535
        for reset,route in [(False,True),(True,False)]:
            with self.assertRaises(ValueError):x.select(reset,route)
            self.assertEqual(x.epoch,65535)
        x.select(True,True);self.assertEqual(x.epoch,0)
    def test_full_shape_no_payload_recharge_and_all12_routes(self):
        r=M.build();self.assertEqual(r['target']['K'],512);self.assertEqual(r['target']['TROWS'],640)
        self.assertEqual(r['incremental']['existing_payload_bits_charged_again'],0)
        self.assertEqual(r['incremental']['existing_staging_bits_charged_again'],0)
        self.assertEqual(r['boundaries']['all12_routes_incremental_signal_track_floor'],540)
        self.assertGreater(r['incremental']['total_state_bits_per_die'],1536)
        self.assertFalse(r['source_successor_plan']['HDL_build_allowed'])
        self.assertTrue(r['source_successor_plan']['component_functional_RTL_writing_allowed'])
    def test_every_numeric_latency_is_an_explicit_unproved_assumption(self):
        r=M.build();self.assertIsNone(r['prospective_bounds']['worst_unrestricted_stall_cycles'])
        self.assertIsNone(r['prospective_bounds']['full_token_delta_cycles'])
        for case in r['prospective_bounds']['sensitivity_assumptions']:
            self.assertFalse(case['source_bound'])
            self.assertEqual(case['publication_cycles'],9*(case['grant_gap']+case['write_or_read_sector_completion_bound']+1))

    def test_group_barrier_is_latched_before_first_caller_new_activity(self):
        g=M.GroupGrant();g.open(True,True,True)
        self.assertEqual(g.accept(0),1)
        # New traffic must not revoke slower callers' already-owned permits.
        with self.assertRaises(ValueError):g.open(False,False,True)
        for rank in [2,1,3]:self.assertEqual(g.accept(rank),1)
        with self.assertRaises(ValueError):g.accept(3)
        with self.assertRaises(ValueError):g.open(False,True,True)
        g.open(True,True,True);self.assertEqual(g.accept(3),2)

    def test_area_uses_actual_ASR_FF_and_only_one_shared_controller(self):
        r=M.build();i=r['incremental']
        self.assertAlmostEqual(i['FF_area_um2'],i['total_state_bits_per_die']*.37908)
        self.assertEqual(i['shared_group_controller_bits'],21)
        self.assertAlmostEqual(i['full4_joined_incremental_slot_um2'],i['all4_slot_um2']+i['shared_group_controller_slot_um2'],places=5)

    def test_Russell_connector_is_lossless_and_not_free_CKV_backing(self):
        h=M.build()['frozen_H4_connector'];c=h['required_if_backing_replaced']
        self.assertEqual(h['existing_clients'],6);self.assertFalse(h['new_seventh_client_admitted'])
        self.assertEqual(c['source_meta_bits'],46+5+9+32)
        self.assertEqual(c['backend_token_bits'],16);self.assertTrue(c['forbid_truncating_high4'])
        self.assertEqual(c['protected_pipeline_increment_bits'],144*38*2*72*2)
        self.assertEqual(c['sidecar_physical_macro_capacity_bits'],4194304)
        self.assertIsNone(c['source_owner_client_SM_allocator'])


if __name__=='__main__':unittest.main()
