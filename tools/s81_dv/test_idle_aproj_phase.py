"""A frame with no a_proj ownership must retain the die-wide phase namespace."""
import copy
import unittest

from layer_prog import xs_place as X
import v41_die_images_w17w10 as I
from field_rank_images import tag_plan


class IdleAproj(unittest.TestCase):
    def test_idle_slot_has_no_executable_payload_or_allocation(self):
        field = I.Field(16, 1, 0, active=10, pp=True, fast=True)
        before = copy.deepcopy((field.fill.tolist(), field.words, field.stream))
        record = X.reserve_idle_aproj(field)
        self.assertEqual((field.fill.tolist(), field.words, field.stream), before)
        self.assertEqual(I.phase_words(field.phases[0]), (0, 0))
        self.assertTrue(record['idle_no_issue'])
        self.assertEqual(record['faults'], 0)
        self.assertTrue(all(word == 0 for pair in field.cfg[0] for word in pair))
        self.assertEqual(len(field.phases), 1)  # next real operation receives phase one
        self.assertEqual(tag_plan(dict(frame='idle', phases=[record]), {})['maps'], {0: []})
        with self.assertRaisesRegex(ValueError, 'no issue programme'):
            X.gen_one(None, None, field, record, None)

    def test_reservation_cannot_shift_an_existing_real_phase(self):
        field = I.Field(16, 1, 0, active=10, pp=True, fast=True)
        X.reserve_idle_aproj(field)
        with self.assertRaises(AssertionError):
            X.reserve_idle_aproj(field)


if __name__ == '__main__':
    unittest.main()
