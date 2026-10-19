"""Actual landing pin identity, including legal unused tie outputs."""
import unittest
from netlist_relay_stages import landing_strap


class LandingStrap(unittest.TestCase):
    def test_every_value_with_only_used_outputs(self):
        for k in range(8):
            cm = {f'k{i}': 'own_hi' if k & (1 << i) else 'own_lo' for i in range(3)}
            if k:
                cm['tie_hi'] = 'own_hi'
            if k != 7:
                cm['tie_lo'] = 'own_lo'
            self.assertEqual(landing_strap(cm), k)

    def test_not_a_literal_or_foreign_rail(self):
        for bad in ("1'b0", "1'b1", 'other_instance_hi', '', 'same'):
            self.assertIsNone(landing_strap(dict(tie_hi='own_hi', tie_lo='own_lo',
                                               k0=bad, k1='own_hi', k2='own_lo')))

    def test_missing_used_output_or_shorted_outputs(self):
        self.assertIsNone(landing_strap(dict(k0='h', k1='h', k2='h', tie_lo='l')))
        self.assertIsNone(landing_strap(dict(k0='x', k1='x', k2='x', tie_hi='x', tie_lo='x')))


if __name__ == '__main__':
    unittest.main()
