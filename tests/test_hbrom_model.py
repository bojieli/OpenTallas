"""Mechanism tests: bank capacity, exact issue padding, and finite resources."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('hbrom_model', Path(__file__).parents[1] / 'tools/hbrom_model.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HBROMModelTests(unittest.TestCase):
    def test_resource_serializes_independent_branches(self):
        nodes = [dict(id='a', duration_ns=10, resources=['compute']),
                 dict(id='b', duration_ns=20, resources=['compute']),
                 dict(id='c', duration_ns=15, resources=['side']),
                 dict(id='join', deps=['a', 'b', 'c'], duration_ns=0)]
        self.assertEqual(m.schedule(nodes)['tpot_ns'], 30)
        self.assertEqual(m.schedule(nodes)['critical_path'], ['a', 'b', 'join'])

    def test_native_groups_are_not_power_of_two_ROM_padding(self):
        # Existing stack pads the reduction internally: no fourth FP4 group.
        self.assertEqual(m.hbrom_allocator.row_geometry('fp4', 5120)['records_per_row'], 24)
        self.assertEqual(m.hbrom_allocator.row_geometry('fp8', 5120)['records_per_row'], 40)
        self.assertEqual(m.hbrom_allocator.row_geometry('bf16', 5120)['records_per_row'], 80)

    def test_unknown_is_not_zero(self):
        with self.assertRaises(ValueError):
            m.schedule([dict(id='missing', duration_ns=None)])

    def test_missing_dependency_rejected(self):
        with self.assertRaises(ValueError):
            m.schedule([dict(id='a', deps=['absent'], duration_ns=0)])

    def test_whole_row_cannot_fractionally_use_empty_tiles(self):
        # One row is 1024 bytes; four 512-byte tiles cannot house that row.
        r = m.pack_stage([dict(name='one', bytes=1024, rows=1)], 1, 1, 4, 512)
        self.assertFalse(r['fits'])
        self.assertEqual(r['max_cluster_bytes'], 1024)

    def test_tensor_tail_and_rank_rounding(self):
        r = m.pack_stage([dict(name='odd', bytes=99, rows=3)], 2, 1, 2, 128)
        self.assertEqual(r['allocated_bytes_per_rank'], 128)
        self.assertEqual(r['useful_bytes_per_rank'], 66)

    def test_replica_storage_not_divided_by_tp(self):
        t = dict(name='replicated', bytes=1024, rows=4, replicated=True)
        r = m.pack_stage([t], 4, 1, 4, 256)
        self.assertEqual(r['useful_bytes_per_rank'], 1024)

    def test_quantized_padded_tree_increases_issue_work(self):
        c = dict(macs_per_cycle={'fp4':256}, weight_ingress_Bpc=136,
                 activation_load_Bpc=256, result_Bpc=4,
                 golden_recurrence_cycles={'fp4':56}, pipeline_cycles=96,
                 clock_ghz=1.2, accumulator_slots=8)
        g = dict(clusters_per_die=1, tiles_per_cluster=1,
                 activation_root_Bpc=256, result_root_Bpc=256, activation_broadcast_cycles=1)
        n = dict(format='fp4', rows=1, k=2304, weight_bytes=1224,
                 activation_bytes=4608, result_bytes=4)
        macro = dict(payload_Bpc={'fp4':34}, capture_cycles=3)
        net = dict(output_streams_per_tile=4, usable_weight_Bpc=136, latency_cycles=4)
        r = m.weight_service(n, g, c, macro, net, 1)
        self.assertEqual(r['padded_k'], 4096)
        self.assertEqual(r['compute_cycles'], 64)
        self.assertGreater(r['cycles'], 96 + 56)


if __name__ == '__main__':
    unittest.main()
