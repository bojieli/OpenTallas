"""Coverage and distinct-entry regressions for physical die clock construction."""
import unittest
from physical_die_clock import graph_pairs, verify_topology


class PhysicalClockTests(unittest.TestCase):
    def test_distinct_child_entries_and_data_pair(self):
        entries = [('vm/ck0', 'VM', 0., 0.), ('vm/ck1', 'VM', 0., 100.),
                   ('relay/ck', 'R', 10., 90.)]
        pairs = graph_pairs(entries, {('vm', 'relay')})
        self.assertIn(('vm/ck0', 'vm/ck1'), pairs)
        self.assertIn(('vm/ck1', 'relay/ck'), pairs)
        self.assertEqual(len(pairs), 2)
        self.assertEqual({frozenset(e) for e in graph_pairs(entries,{'vm':{'relay'},'relay':{'vm'}})},
                         {frozenset(e) for e in pairs})

    def test_missing_leaf_and_double_drive_are_refused(self):
        tree = dict(buffers=[('a', 'BUF', 0., 0.)], nets=[
            ('root', ('port', 'clk_hbm'), [('buf', 'a')]),
            ('leaf', ('buf', 'a'), [('pin', 'tile/ck', 'entry')])])
        self.assertEqual(verify_topology(tree, ['tile/ck'])['covered_entries'], 1)
        with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
            verify_topology(tree, ['tile/ck', 'tile/other_child'])
        broken = dict(tree, nets=tree['nets'] + [('second', ('buf', 'a'), [('pin', 'tile/ck', 'entry')])])
        with self.assertRaisesRegex(ValueError, 'multiple nets'):
            verify_topology(broken, ['tile/ck'])

    def test_disconnected_buffer_is_refused(self):
        tree = dict(buffers=[('orphan', 'BUF', 0., 0.)], nets=[
            ('root', ('port', 'clk_hbm'), [('pin', 'tile/ck', 'entry')])])
        with self.assertRaisesRegex(ValueError, 'orphan'):
            verify_topology(tree, ['tile/ck'])


if __name__ == '__main__':
    unittest.main()
