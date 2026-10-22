"""Regress the actual generated sticky comparator against reset/reassertion."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("lp", Path(__file__).with_name("lp.py"))
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)


def lower(history, offset=1, lag=12):
    expr = lp.sticky_history_ref("fault", offset, lag)
    return eval(expr, {}, {"fo_fault": history[0], "dlo_fault": history[1:]})


class StickyEpochTests(unittest.TestCase):
    def test_old_epoch_must_not_accelerate_new_assertion(self):
        history = [1, 1, 1] + [0] * 4 + [1] * 10
        self.assertEqual(history[1] & history[13], 1)  # old comparator false positive
        self.assertEqual(lower(history), 0)

    def test_missing_continuously_asserted_fault_still_fails(self):
        self.assertEqual(lower([1] * 17), 1)

    def test_vector_bits_have_independent_assertion_ages(self):
        self.assertEqual(lower([3, 3, 3, 1] + [3] * 13), 1)

    def test_reset_at_each_window_position(self):
        for age in range(1, 14):
            history = [1] * 17
            history[age] = 0
            self.assertEqual(lower(history), 0)

    def test_zero_offset_and_zero_lag(self):
        self.assertEqual(lower([3], offset=0, lag=0), 3)
        self.assertEqual(lower([3, 1], offset=1, lag=0), 1)

    def test_boundary_does_not_include_unrelated_older_history(self):
        self.assertEqual(lower([1] * 14 + [0] * 3), 1)


if __name__ == "__main__":
    unittest.main()
