import unittest
from die_case_v16 import validate_view_coverage


class ViewCoverageTest(unittest.TestCase):
    def test_new_relay_instance_requires_current_view_plan(self):
        with self.assertRaisesRegex(ValueError, 'stale views.json: 1'):
            validate_view_coverage({'old': {}, 'rly0000_s000_t0': {}},
                                   {'relay': {'instances': ['old']}})

    def test_missing_synth_receipt_stays_separate_from_membership(self):
        validate_view_coverage({'idx': {}, 'relay': {}},
                               {'idx': {'instances': ['idx']}, 'rly': {'instances': ['relay']}})

    def test_duplicate_membership_refused(self):
        with self.assertRaisesRegex(ValueError, 'duplicate view membership'):
            validate_view_coverage({'x': {}}, {'a': {'instances': ['x']}, 'b': {'instances': ['x']}})


if __name__ == '__main__':
    unittest.main()
