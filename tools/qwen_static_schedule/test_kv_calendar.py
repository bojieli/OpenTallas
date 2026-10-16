"""Capacity bounds and fail-closed separation from a real 36-layer programme."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule import kv_calendar as K
from qwen_static_schedule.calendar import ScheduleError

P = dict(K.SOURCED, ring_cdc_core_edges=3, layer_period_core=6639, write_ready_core=0, refresh=dict(edges_per_layer=0))


class KvCalendar(unittest.TestCase):
    def test_inputs_required(self):
        with self.assertRaises(ScheduleError):
            K.compile_layer(8192, dict(K.SOURCED))

    def test_current_sizes_infeasible(self):
        r = K.compile_36(8192, P)
        self.assertFalse(r['capacity_feasible'])
        self.assertGreater(r['layer']['ring_peak'], P['ring_depth'])
        self.assertLess(r['layer']['front_credit_rate'], 0.5)       # NBLK 4 x 8 credit-limits the K stream

    def test_sized_boundary_has_capacity_but_no_programme_qualification(self):
        q = dict(P, front_nblk=12, ring_depth=64)
        r = K.compile_36(8192, q)
        self.assertTrue(r['capacity_feasible'])
        self.assertEqual(r['layer']['ring_peak'], 48)                # = the 256 x (1 - 833.3/1024) frequency prefill
        self.assertEqual(r['layer']['k_rd_core_edges'], 315)
        self.assertFalse(r['feasible'])
        self.assertFalse(r['production_schedule_qualified'])
        self.assertFalse(r['write_readiness_checked'])
        self.assertEqual(r['own_row_scan_index'], [255])             # the token's own K row is the last K read

    def test_refresh_as_implemented_keeps_resized_boundary(self):
        q = dict(P, front_nblk=10, ring_depth=64, refresh=K.refresh_from_table())
        self.assertEqual(q['refresh']['block_hbm'], 0)               # REF_MODE 1: rd_block = 0
        r = K.compile_36(8192, q)
        self.assertTrue(r['capacity_feasible'])
        self.assertEqual(r['layer']['ring_peak'], 48)

    def test_refresh_upper_bound_needs_deeper_ring(self):
        q = dict(P, front_nblk=10, ring_depth=64, refresh=K.refresh_from_table(bound='upper'))
        r = K.compile_36(8192, q)
        self.assertFalse(r['capacity_feasible'])
        self.assertEqual(r['layer']['ring_peak'], 67)
        self.assertEqual(r['layer']['refresh_offsets'], 118)

    def test_actual_issue_is_not_a_raw_sector_index(self):
        r = K.compile_36(8192, P)
        self.assertGreater(r['own_row_rd_issue_hbm_after_prefetch'][0], 255)

    def test_impossibly_late_write_is_rejected_by_explicit_origin(self):
        q = dict(P, front_nblk=16, ring_depth=64,
                 write_ready_core=1000000, write_ready_origin='prefetch_start')
        r = K.compile_36(8192, q)
        self.assertTrue(r['capacity_feasible'])
        self.assertTrue(r['write_readiness_checked'])
        self.assertFalse(r['own_row_read_after_write_ok'])
        self.assertFalse(r['feasible'])

    def test_unknown_write_time_origin_refuses(self):
        with self.assertRaises(ScheduleError):
            K.compile_36(8192, dict(P, write_ready_origin='somewhere'))


if __name__ == '__main__':
    unittest.main()
