"""The token consumer must not silently price stale or relabelled lane costs."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('current_pricing', Path(__file__).with_name('compose_tok_ds.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CurrentLatency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(m.PLAN.read_text())
        # Current in-plan G0 table, independently maintained by the die owner.
        cls.current = dict(plan_digest=m.plan_digest(cls.raw), period_ps=833,
                           lanes=cls.raw['latency']['lanes'])

    def test_current_plan_lanes_are_accepted(self):
        m.validate_lane_table(self.current, self.raw)

    def test_stale_digest_is_rejected(self):
        bad = copy.deepcopy(self.current)
        bad['plan_digest'] = 'bd2b875cbfbb7e24'
        with self.assertRaisesRegex(ValueError, 'stale'):
            m.validate_lane_table(bad, self.raw)

    def test_relabelled_wrong_cost_is_rejected(self):
        bad = copy.deepcopy(self.current)
        next(iter(bad['lanes'].values()))['cycles'] += 1
        with self.assertRaisesRegex(ValueError, 'differs from plan'):
            m.validate_lane_table(bad, self.raw)

    def test_missing_lane_is_rejected(self):
        bad = copy.deepcopy(self.current)
        bad['lanes'].pop(next(iter(bad['lanes'])))
        with self.assertRaisesRegex(ValueError, 'lane set'):
            m.validate_lane_table(bad, self.raw)


if __name__ == '__main__':
    unittest.main()
