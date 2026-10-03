import importlib.util
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/model_dsrom_ckv_receive_credit.py'
SPEC = importlib.util.spec_from_file_location('ckv_receive_model', PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ReceiveLeaseModelTests(unittest.TestCase):
    def test_all512_permutations_both_passes_all4_ranks(self):
        # Per-rank input bytes remain immutable even across arbitrary full occupancy/stalls.
        for die in range(4):
            ids = [4096 + 3*i for i in range(512)]
            p = M.Lease(ids)
            order = list(range(512))
            random.Random(2000+die).shuffle(order)
            for rank in order:
                p.accept(0, rank, ids[rank], (rank, ids[rank], die))
            before = dict(p.rows)
            for phase in range(2):
                got = []
                for beat in range(128):
                    self.assertEqual(p.take(False), [])
                    got.extend(p.take(True))
                self.assertEqual([r for r, _ in got], list(range(512)))
                self.assertEqual(dict(got), before)
                p.retire_descriptor(True)
            p.release(True, set(range(9)))
            self.assertEqual(p.rows, before)

    def test_reject_stale_duplicate_bad_identity_and_bounds_without_mutation(self):
        p = M.Lease(list(range(512)))
        p.accept(0, 0, 0, 123)
        for epoch, rank, gid in [(1,1,1),(0,0,0),(0,1,2),(0,512,512),(0,1023,1023),(0,-1,-1)]:
            before = dict(p.rows)
            with self.subTest(epoch=epoch, rank=rank, gid=gid):
                with self.assertRaises(ValueError):
                    p.accept(epoch, rank, gid, 999)
                self.assertEqual(p.rows, before)

    def test_missing_first_rank_holds_without_losing_later511(self):
        p = M.Lease(list(range(512)))
        for rank in range(1,512):
            p.accept(0, rank, rank, rank)
        self.assertEqual(p.take(True), [])
        self.assertEqual(len(p.rows), 511)
        p.accept(0,0,0,0)
        self.assertEqual(p.take(True), [(i,i) for i in range(4)])

    def test_qk_take_does_not_return_lease_credit(self):
        p = M.Lease(list(range(512)))
        for i in range(512):
            p.accept(0,i,i,i)
        for _ in range(128):
            p.take(True)
        with self.assertRaises(ValueError):
            p.release(True,set(range(9)))
        with self.assertRaises(ValueError):
            p.retire_descriptor(False)
        p.retire_descriptor(True)
        with self.assertRaises(ValueError):
            p.release(True,set(range(9)))
        self.assertEqual(len(p.rows),512)

    def test_two_passes_need_all_publication_and_reverse_fences(self):
        p = M.Lease(list(range(512)))
        for i in range(512):
            p.accept(0,i,i,i)
        for phase in range(2):
            for _ in range(128):
                p.take(True)
            p.retire_descriptor(True)
        for reverse, visible in [(False,set(range(9))),(True,set(range(8)))]:
            with self.assertRaises(ValueError):
                p.release(reverse,visible)
        p.release(True,set(range(9)))
        with self.assertRaises(ValueError):
            p.take(True)

    def test_pin_tamper_refuses_before_model(self):
        with tempfile.TemporaryDirectory() as d:
            copied = Path(d)/'archive'
            shutil.copytree(M.BASE, copied)
            pin = json.loads((copied/'origins.json').read_text())['origins'][0]
            (copied/pin['archive']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'archived source changed'):
                M.build(copied)

    def test_model_no_stall_bound_or_installed_adoption(self):
        r = M.build()
        self.assertIsNone(r['occupancy']['worst_stall_cycles'])
        self.assertFalse(r['scope']['launch_allowed'])
        self.assertEqual(r['scope']['installed_binary_binding'],'UNPROVEN')
        self.assertEqual(r['occupancy']['payload_bytes_per_rank'],147456)
        self.assertEqual(r['ports']['expanded_stage_write_bits'],16960)
        self.assertEqual(r['ports']['remote_payload_bits_per_edge'],6912)
        self.assertEqual(r['occupancy']['QK_PV_additional_collector_buffers'],0)
        self.assertIsNone(r['storage_area']['actual_slot'])

    def test_original_failures_unchanged_and_service_same_as_historical(self):
        pins = M.verify_inputs()['origins']
        p = next(x for x in pins if x['path']=='rtl/chip/ot_chip_v41x_ckv_die_service.sv')
        old = json.loads((M.BASE/'inputs/historical_ckv_b93_r1.json').read_text())
        self.assertEqual(p['sha256'],old['source_sha256'][p['path']])
        x=json.loads((M.BASE/'inputs/results/rtl/w17_connected_token_preparation_20261001/ckv_delayed_peer_counterexample.json').read_text())
        self.assertIn('old_payload_stored=1 fault=0',x['log'])
        self.assertFalse(x['hardware_admission'])

    def test_current_runtime_inventory_has_original_service_not_local_fix(self):
        r=M.build()
        self.assertIn('w17_current_fastpp_l20_sources',r['bindings']['source_inventory'])
        self.assertIn('no service selection ready',r['equations']['selection_caller'])
        self.assertGreaterEqual(r['archived_input_count'],34)

    def test_epoch_is_lease_state_not_mutable_receive_argument(self):
        p=M.Lease(list(range(512)),epoch=7)
        with self.assertRaises(ValueError):
            p.accept(0,0,0,0)
        p.accept(7,0,0,99)
        self.assertEqual(p.take(True),[(0,99)])

    def test_two_buffer_control_no_same_edge_free_reuse(self):
        c=M.merger_control_calendar()
        self.assertEqual(c['intake_edges'][:6],[0,1,3,4,6,7])
        self.assertEqual(c['emit_edges'][:6],[2,3,5,6,8,9])
        self.assertEqual(len(c['intake_edges']),128)
        self.assertEqual(len(c['emit_edges']),128)
        self.assertEqual(c['edges_first_intake_through_final_emit'],193)
        self.assertEqual(c['emit_edges'][-1],192)


if __name__ == '__main__':
    unittest.main()
