import unittest
from tools.hbm_die_v15.grant_slot_bind import resolve_slot


class GrantBindingTest(unittest.TestCase):
    def test_explicit_instance_home_beats_stale_alias(self):
        inst = {'master': 'scorer', 'slot': 'idx_s0_h0'}
        slots = {'hb_idx__s_SW': {'instance': 'hb_idx__s_SW', 'cell': 'scorer'}}
        self.assertEqual(resolve_slot('hb_idx__s_SW', inst, slots, {}), 'hb_idx__s_SW')
        self.assertEqual(resolve_slot('hb_idx__s_SW', inst, slots, {}, 'manual'), 'manual')

    def test_mismatched_master_cannot_claim_a_grant(self):
        with self.assertRaises(ValueError):
            resolve_slot('x', {'master': 'new'}, {'x': {'instance': 'x', 'cell': 'old'}}, {})

    def test_unbound_legacy_grants_keep_existing_behavior(self):
        self.assertEqual(resolve_slot('x', {'master': 'm', 'slot': 'legacy'}, {'x': {'cell': 'm'}}, {}), 'legacy')


if __name__ == '__main__':
    unittest.main()
