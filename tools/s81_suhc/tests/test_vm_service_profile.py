import copy
import importlib.util
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('reservations', HERE / 'static_vm_reservations.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import vm_service_profile as VSP  # noqa: E402

NAME = 's81_vm_r4_c2_w1'


class SelectedProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        manifest = json.loads((VSP.ROOT / VSP.MEASURED_MANIFEST).read_text())
        for path in set(manifest) | set(VSP.PROFILES[NAME]['receipts']) | {VSP.MEASURED_MANIFEST}:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(VSP.ROOT / path, target)
        self.contract = dict(stream_period_ps=833, vm_period_ps=833, stream_phase_ps=0, vm_phase_ps=0,
            banks=32, bank_mapping='xor_row7_5_shift2', bank_queue_capacity=4, bank_ops_per_cycle=1, read_ingress_per_cycle=1, write_ingress_per_cycle=1,
            request_min_ps=0, read_min_ps=0, commit_min_ps=0,
            slot_capacity={'su/write/0': 1, 'su/read/0': 1}, client_capacity={'su': 2},
            vm_service_profile=dict(name=NAME, rtl_tuple=dict(READ_PIPE=4, CAP_PIPE=2, WSCATTER_PIPE=1),
                                    evidence=VSP.evidence_for(NAME, self.root)))
        # write at pin P=0 lane 0: raw w_ce P+10, returned commit P+12; dependent read at Q=4: raw r_ce Q+7=11 > 10
        self.schedule = dict(trace_complete=True, events=[
            dict(id='w', kind='write', client='su', slot=0, row=64, tag=0, lane=0, issue_cycle=0, ingress_cycle=1,
                 bank_enqueue_cycle=1, service_cycle=10, raw_cycle=10, commit_cycle=12, deadline_cycle=12),
            dict(id='r', kind='read', client='su', slot=0, row=64, tag=1, issue_cycle=4, ingress_cycle=5,
                 bank_enqueue_cycle=5, service_cycle=11, raw_cycle=11, response_cycle=20, deadline_cycle=20)],
            jobs=[dict(client='su', tag=0, done_cycle=12), dict(client='su', tag=1, done_cycle=20)],
            dependencies=[dict(producer='w', consumer='r')])

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self):
        return m.check(self.schedule, self.contract, source_root=self.root)

    def kinds(self):
        r = self.run_check()
        return {x['kind'] for x in r['violations']} | ({'invalid:' + f for v in r['violations'] for f in v.get('fields', [])})

    def test_exact_selected_calendar_passes(self):
        snap = copy.deepcopy(self.schedule)
        r = self.run_check()
        self.assertEqual(r['status'], 'pass', r['violations']); self.assertFalse(r['qualified'])
        self.assertEqual(r['vm_service_profile'], NAME); self.assertEqual(snap, self.schedule)

    def test_raw_read_one_edge_early_rejected(self):
        # Q = P+3: raw read P+10 on the same edge as the raw write -> old value (read-before-write)
        self.schedule['events'][1].update(issue_cycle=3, raw_cycle=10, service_cycle=10, response_cycle=19, deadline_cycle=19)
        self.schedule['jobs'][1]['done_cycle'] = 19
        self.assertIn('profile_consume_before_raw_write', self.kinds())

    def test_legal_raw_read_before_returned_commit_admitted(self):
        # Q=P+4 reads at raw P+11, before the returned commit P+12: legal (returned commit is only the done fence)
        self.assertNotIn('consume_before_commit', self.kinds())

    def test_stale_l15_read_minimum_rejected(self):
        self.schedule['events'][1].update(response_cycle=19, deadline_cycle=19)
        self.assertIn('profile_read_return_edge', self.kinds())

    def test_stale_k11_commit_rejected(self):
        self.schedule['events'][0].update(commit_cycle=11, deadline_cycle=11)
        self.assertIn('profile_write_returned_commit_edge', self.kinds())

    def test_lane_shifts_write_edges(self):
        self.schedule['events'][0].update(lane=2)
        k = self.kinds()
        self.assertIn('profile_write_raw_edge', k); self.assertIn('profile_write_returned_commit_edge', k)

    def test_missing_lane_rejected(self):
        del self.schedule['events'][0]['lane']
        self.assertIn('profile_write_lane_unbound', self.kinds())

    def test_disconnected_service_edge_rejected(self):
        # Correct raw/return ages cannot conceal an invented bank-use cycle.
        self.schedule['events'][0]['service_cycle'] = 9
        self.assertIn('profile_service_raw_edge_mismatch', self.kinds())

    def test_service_and_raw_domains_compare_physical_time(self):
        self.contract['vm_period_ps'] = 416.5
        for event in self.schedule['events']:
            for field in ('ingress_cycle', 'bank_enqueue_cycle', 'service_cycle'):
                event[field] *= 2
        self.assertEqual(self.run_check()['status'], 'pass')
        self.contract['vm_phase_ps'] = 1
        self.assertIn('profile_service_raw_edge_mismatch', self.kinds())

    def test_noninteger_raw_edge_rejected(self):
        self.schedule['events'][0]['raw_cycle'] = 10.0
        self.assertIn('profile_raw_cycle_unbound', self.kinds())

    def test_wrong_bank_map_rejected(self):
        self.contract['bank_mapping'] = 'rowmod'
        self.assertIn('invalid:vm_service_profile_bank_mapping_mismatch', self.kinds())

    def test_invented_bank_capacity_rejected(self):
        self.contract['bank_ops_per_cycle'] = 2
        self.assertIn('invalid:vm_service_profile_bank_capacity_mismatch', self.kinds())

    def test_stale_source_invalidates_profile(self):
        (self.root / VSP.RTL_SOURCES[0]).write_text('edited')
        self.assertTrue(any(x.startswith('invalid:vm_service_profile_stale') for x in self.kinds()))

    def test_rehashed_unlisted_latency_stage_is_not_a_measurement(self):
        path = 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_return_bank8.sv'
        self.assertNotIn(path, VSP.RTL_SOURCES)
        with (self.root / path).open('a') as stream:
            stream.write('\n// changed return pipeline stage\n')
        self.contract['vm_service_profile']['evidence'] = VSP.evidence_for(NAME, self.root)
        self.assertIn('invalid:vm_service_profile_unmeasured_source:' + path, self.kinds())

    def test_rehashed_listed_source_is_not_a_measurement(self):
        path = VSP.RTL_SOURCES[0]
        with (self.root / path).open('a') as stream:
            stream.write('\n// new pipeline, without a new measurement\n')
        self.contract['vm_service_profile']['evidence'] = VSP.evidence_for(NAME, self.root)
        self.assertIn('invalid:vm_service_profile_unmeasured_source:' + path, self.kinds())

    def test_rehashed_rewritten_measurement_manifest_rejected(self):
        path = self.root / VSP.MEASURED_MANIFEST
        path.write_text('{}')
        self.contract['vm_service_profile']['evidence'] = VSP.evidence_for(NAME, self.root)
        self.assertIn('invalid:vm_service_profile_unmeasured_artifact:' + VSP.MEASURED_MANIFEST, self.kinds())

    def test_external_cdc_and_testbench_do_not_redefine_core_ages(self):
        for path in VSP.OUTSIDE_PROFILE_BOUNDARY:
            (self.root / path).write_text('// outside profile boundary\n')
        self.assertEqual(self.run_check()['status'], 'pass')

    def test_wrong_tuple_invalidates_profile(self):
        self.contract['vm_service_profile']['rtl_tuple']['WSCATTER_PIPE'] = 0
        self.assertIn('invalid:vm_service_profile_rtl_tuple_mismatch', self.kinds())

    def test_no_profile_keeps_legacy_minima(self):
        del self.contract['vm_service_profile']
        self.contract['measured_native_bounds'] = True
        r = self.run_check()
        self.assertNotIn('vm_service_profile', [v['kind'] for v in r['violations']])
        self.assertIsNone(r['vm_service_profile'])


if __name__ == '__main__':
    unittest.main()
