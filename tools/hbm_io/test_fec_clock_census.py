import unittest
from fec_clock_census import census


class ClockOwnership(unittest.TestCase):
    def fixture(self):
        return {'modules': {'top': {
            'ports': {'a': {'direction': 'input', 'bits': [1]},
                      'b': {'direction': 'input', 'bits': [2]}},
            'cells': {'flop': {'type': '$adff', 'connections': {'CLK': [1], 'Q': [3, 4]}},
                      'other': {'type': '$dffe', 'connections': {'CLK': [2], 'Q': [5]}}}}}}

    def test_actual_q_bits_not_register_cell_count(self):
        r = census(self.fixture(), 'top', ['a', 'b'])
        self.assertEqual(r['clock_flop_bits'], {'a': 2, 'b': 1})
        self.assertEqual(r['total_flop_bits'], 3)

    def test_generated_clock_cannot_masquerade_as_delivered_root(self):
        d = self.fixture(); d['modules']['top']['cells']['flop']['connections']['CLK'] = [10]
        with self.assertRaisesRegex(ValueError, 'not a declared delivered'):
            census(d, 'top', ['a', 'b'])

    def test_hidden_state_or_hierarchy_is_rejected(self):
        for kind in ('$dlatch', '$mem_v2', '$ff', '$sr', '$fsm', '$anyseq',
                     'unresolved_child'):
            with self.subTest(kind=kind):
                d = self.fixture(); d['modules']['top']['cells']['bad'] = {'type': kind}
                with self.assertRaises(ValueError):
                    census(d, 'top', ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
