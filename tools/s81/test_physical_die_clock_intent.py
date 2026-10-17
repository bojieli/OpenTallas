"""Clock intent must come from source bus classes, never signal-name heuristics."""
import unittest
from physical_die_clock_intent import intents


class ClockIntentTests(unittest.TestCase):
    def test_forwarded_clock_retained_and_clock_named_data_ignored(self):
        model=dict(buses=[['ck_enable','control',1,[['a','en','out'],['b','en','in']]],
            ['forward','fclk',1,[['a','fo0','out'],['b','fi0','in']]],
            ['trunk','clock',1,[['pll','out','out'],['b','ck','in']]]])
        self.assertEqual([x[0] for x in intents(model)],['forward','trunk'])

    def test_vector_clock_without_per_bit_map_is_refused(self):
        with self.assertRaisesRegex(ValueError,'per-bit map'):
            list(intents(dict(buses=[['clockvec','fclk',2,[['a','o','out'],['b','i','in']]]])))


if __name__=='__main__':unittest.main()
