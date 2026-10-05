import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('vmorder', ROOT / 'tools/dsrom_split_vm_order_model.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class VMContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = m.build()

    def test_read_old_even_after_write_in_source(self):
        replies, image, _ = m.ordered_edge({12: 123}, [('r', 12)], [('w', 12, 456)])
        self.assertEqual(replies['r'], 123)
        self.assertEqual(image[12], 456)

    def test_superseded_write_never_visible(self):
        _, image, receipts = m.ordered_edge({}, [], [('field', 7, 1), ('QE', 7, 2)])
        self.assertEqual(image[7], 2)
        self.assertEqual(receipts, {'field': 'SUPERSEDED_NOT_VISIBLE', 'QE': 'VISIBLE_WINNER'})

    def test_collective_lane_priority(self):
        writes = [('package', 3, 10)] + [('bank' + str(i), 3, i) for i in range(4)]
        _, image, receipts = m.ordered_edge({}, [], writes)
        self.assertEqual(image[3], 3)
        self.assertEqual(sum(v == 'VISIBLE_WINNER' for v in receipts.values()), 1)

    def test_lane_loop_last_wins(self):
        _, image, receipts = m.ordered_edge({}, [], [('lane0', 2, 1), ('lane1', 2, 2)])
        self.assertEqual(image[2], 2)
        self.assertEqual(receipts['lane0'], 'SUPERSEDED_NOT_VISIBLE')

    def test_bounds_not_silently_wrapped(self):
        with self.assertRaises(ValueError):
            m.ordered_edge({}, [], [('w', 1 << 19, 1)])
        with self.assertRaises(ValueError):
            m.ordered_edge({}, [('r', -1)], [])

    def test_uninitialized_memory_not_synthetic_zero(self):
        with self.assertRaises(KeyError):
            m.ordered_edge({}, [('r', 1)], [])

    def test_transaction_identity(self):
        with self.assertRaises(ValueError):
            m.ordered_edge({}, [], [('w', 1, 1), ('w', 2, 2)])

    def test_duplicate_read_identity_refused_before_lookup(self):
        for reads in [[('r', 1), ('r', 2)], [('r', 1), ('r', 1)]]:
            with self.subTest(reads=reads), self.assertRaisesRegex(ValueError, 'Read transaction identity reused'):
                m.ordered_edge({}, reads, [])

    def test_same_address_fanout_keeps_distinct_requests(self):
        replies, _, _ = m.ordered_edge({1: 123}, [('r0', 1), ('r1', 1)], [])
        self.assertEqual(replies, {'r0': 123, 'r1': 123})

    def test_finite_iterator_requests_not_consumed_by_validation(self):
        replies, image, _ = m.ordered_edge({1: 123, 2: 456}, iter([('r0', 1), ('r1', 2)]), iter([('w', 2, 789)]))
        self.assertEqual(replies, {'r0': 123, 'r1': 456})
        self.assertEqual(image[2], 789)

    def test_noninteger_addresses_refused_both_directions(self):
        for address in [True, False, 1.0, '1', None]:
            with self.subTest(address=address), self.assertRaises(ValueError):
                m.ordered_edge({1: 123}, [('r', address)], [])
            with self.subTest(address=address), self.assertRaises(ValueError):
                m.ordered_edge({}, [], [('w', address, 123)])

    def test_read_write_address_boundaries(self):
        last = (1 << 19) - 1
        replies, image, _ = m.ordered_edge({0: 1, last: 2}, [('r0', 0), ('r1', last)], [('w', last, 3)])
        self.assertEqual(replies, {'r0': 1, 'r1': 2})
        self.assertEqual(image[last], 3)
        for address in [-1, 1 << 19]:
            with self.subTest(address=address), self.assertRaises(ValueError):
                m.ordered_edge({}, [('r', address)], [])
            with self.subTest(address=address), self.assertRaises(ValueError):
                m.ordered_edge({}, [], [('w', address, 123)])

    def test_invalid_identity_refused_both_directions(self):
        for identity in [True, 1.0, [], None, '', -1]:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                m.ordered_edge({1: 123}, [(identity, 1)], [])
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                m.ordered_edge({}, [], [(identity, 1, 123)])

    def test_idle_requires_actual_drain_and_epoch(self):
        self.assertTrue(m.idle_join(True, 0, 0, 0, True, True))
        for p, w, j in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
            self.assertFalse(m.idle_join(True, p, w, j, True, True))
        self.assertFalse(m.idle_join(True, 0, 0, 0, False, True))
        self.assertFalse(m.idle_join(True, 0, 0, 0, True, False))

    def test_issue_mask_not_all_unit_barrier(self):
        self.assertTrue(m.source_waited(1, 1, 0))
        self.assertFalse(m.source_waited(1, 1, 1))
        self.assertFalse(m.source_waited(31, 1, 0))

    def test_finite_service_requires_nonzero_contract(self):
        self.assertEqual(m.finite_batches(65, 16, 3, 2), 17)
        for args in [(1, 0, 1, 1), (1, 1, 0, 1), (1, 1, 1, 0), (-1, 1, 1, 1)]:
            with self.assertRaises(ValueError):
                m.finite_batches(*args)

    def test_actual_selected_demand(self):
        x = self.model['demand_envelope']
        self.assertEqual(x['read_element_ports'], 1520)
        self.assertEqual(x['write_element_ports'], 593)
        self.assertEqual(x['read_bytes_per_chain_cycle'], 6080)
        self.assertEqual(x['write_bytes_per_chain_cycle'], 2372)

    def test_no_small_VM_or_fitted_parent_claim(self):
        self.assertEqual(self.model['capacity']['bits'], 16777216)
        self.assertFalse(self.model['admission']['engine_RTL'])
        self.assertFalse(self.model['admission']['physical'])
        self.assertFalse(self.model['admission']['full_token'])

    def test_no_blanket_pinaccess_reclassification(self):
        x = self.model['pin_access_review']
        self.assertEqual(x['confirmed_historical_cause'], 'p12q9 only')
        self.assertEqual(x['independent_tests'], 7)
        self.assertIn('negative timing', x['other_R0_MY'])


if __name__ == '__main__':
    unittest.main()
