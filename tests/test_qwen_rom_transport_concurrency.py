import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('q2', ROOT/'tools/qwen_rom_transport_concurrency.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)

class Transport(unittest.TestCase):
    def test_exact_little_law(self):
        r=q.size(4194304,4668,41)
        self.assertEqual(r['minimum_sector_credits_global'],1152)
        self.assertEqual(r['balanced_minimum_sector_credits_per_stack'],288)
        self.assertEqual(r['payload_bytes_per_cycle_exact'],'1048576/1167')
    def test_serial_ownership_not_removed_by_credits(self):
        r=q.build()
        self.assertEqual(r['finite_candidate']['source_owner_floor_cycles'],393216)
        self.assertFalse(r['finite_candidate']['queue_capacity_admits_target_throughput'])
        self.assertTrue(r['scenarios']['row_hit']['sixteen_burst_credits_satisfy_service_only_bound'])
    def test_conflict_credits_and_commands(self):
        r=q.build()['scenarios']['row_conflict']
        self.assertEqual(r['minimum_sector_credits_global'],2331)
        self.assertEqual(r['balanced_minimum_sector_credits_per_stack'],583)
        self.assertEqual(r['balanced_burst_records_per_stack'],19)
        self.assertEqual(r['command_lanes_per_stack'],22)
        self.assertFalse(r['sixteen_burst_credits_satisfy_service_only_bound'])
    def test_refresh_not_worstcase(self):
        r=q.build()['scenarios']['row_conflict_plus_refresh']
        self.assertEqual(r['minimum_sector_credits_global'],14124)
        self.assertEqual(r['balanced_burst_records_per_stack'],111)
        self.assertIn('RD-only',r['command_floor_scope'])
    def test_II1_one_port_still_cannot_fit(self):
        r=q.size(4194304,4668,41,owner_ii=1,return_ii=1)
        self.assertEqual(r['source_floor_cycles']['owner'],32768)
        self.assertEqual(r['sector_return_lanes_global'],29)
        self.assertEqual(r['balanced_sector_return_lanes_per_stack'],8)
    def test_actual_window_argument_changes_all_bounds(self):
        r=q.size(4194304,131072,41)
        self.assertEqual(r['minimum_sector_credits_global'],41)
        self.assertEqual(r['sector_return_lanes_global'],1)
        self.assertEqual(r['fill_64B_lanes_global'],1)
        with self.assertRaises(ValueError):q.size(4194304,0,41)
    def test_traffic_and_capacity_not_admission(self):
        r=q.build()
        self.assertEqual(r['traffic']['incremental_bulk_bytes'],0)
        self.assertEqual(r['traffic']['existing_bytes_per_die_token'],36*4194304)
        self.assertEqual(r['local_window']['two_padded_windows_bytes'],8650752)
        self.assertLess(r['local_window']['two_padded_windows_bytes'],12582912)
        self.assertFalse(r['build_admitted'])
        self.assertFalse(r['calibrated_rate'])
        self.assertIsNone(r['reference']['actual_context8K_available_prefetch_cycles'])
    def test_proxy_ledger_and_exclusions(self):
        r=q.build()
        self.assertEqual(sum(v['bits'] for v in r['area_structural_price'].values()),899552)
        self.assertAlmostEqual(r['area_FF50_proxy_sum_mm2'],0.5246187264)
        self.assertEqual(r['conditional_successor_interface']['payload_bits_per_cycle'],8192)
        self.assertIsNone(r['mux_demux']['cell_area_mm2'])
    def test_reverse_echo_is_separate_throughput_demand(self):
        r=q.build()
        self.assertEqual(r['finite_candidate']['shared_owned_data_and_credit_echo_floor_cycles'],65536)
        p=r['conditional_successor_interface']
        self.assertEqual(p['owned_boundary_bits_per_cycle'],64*465)
        self.assertEqual(p['reverse_credit_input_bits_per_cycle'],32*210)
    def test_source_tamper_refused(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)
            for p in q.INPUT.iterdir(): (dest/p.name).write_bytes(p.read_bytes())
            (dest/'candidate.json').write_text('{}')
            with patch.object(q,'INPUT',dest),self.assertRaises(ValueError):q.build()
    def test_deterministic_offline_replay(self):
        self.assertEqual(q.build(),q.build())

if __name__=='__main__':unittest.main()
