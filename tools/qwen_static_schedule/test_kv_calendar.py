"""36-layer static KV calendar at the 0az boundary: current front/ring sizes are infeasible, the sized ones close."""
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
        self.assertFalse(r['feasible'])
        self.assertGreater(r['layer']['ring_peak'], P['ring_depth'])
        self.assertLess(r['layer']['front_credit_rate'], 0.5)       # NBLK 4 x 8 credit-limits the K stream

    def test_sized_boundary_closes_36_layers(self):
        q = dict(P, front_nblk=12, ring_depth=64)
        r = K.compile_36(8192, q)
        self.assertTrue(r['feasible'])
        self.assertEqual(r['layer']['ring_peak'], 48)                # = the 256 x (1 - 833.3/1024) frequency prefill
        self.assertEqual(r['layer']['k_rd_core_edges'], 315)
        self.assertEqual(r['own_row_scan_index'], [255])             # the token's own K row is the last K read


if __name__ == '__main__':
    unittest.main()
