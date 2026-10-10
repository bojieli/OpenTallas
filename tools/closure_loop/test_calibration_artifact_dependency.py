"""Artifact-derived route timing must wait for its own completed CTS database."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl


class CalibrationArtifactDependency(unittest.TestCase):
    def test_tap_route_waits_despite_historical_measurement(self):
        job = {'name': 'vm8', 'stage_idx': 0, 'spec': {'stages': {
            'calibrate': {'cmd': 'cts'},
            'route': {'cmd': 'python3 physical/hbm_accel_die_views/vm/vcut8/tap_latency.py --base own_cts && route'}}}}
        before = copy.deepcopy(job)
        with patch.object(cl, 'assumed_insertion', return_value=({'CK_SS_MEAN': 160, 'CK_FF_MEAN': 133}, 'history')) as assumed, patch.object(cl, 'ssh') as ssh:
            result = cl.start_parallel_calibrate(job, [], job['spec']['stages']['calibrate'])
        self.assertFalse(result)
        assumed.assert_not_called()
        ssh.assert_not_called()
        self.assertEqual(job['stage_idx'], before['stage_idx'])
        self.assertNotIn('ctrack', job)
        self.assertIn('requires completed calibration artifacts', job['events'][-1])

    def test_explicit_artifact_requirement_waits(self):
        job = {'name': 'other', 'stage_idx': 0, 'spec': {'stages': {'calibrate': {'cmd': 'cts', 'base': '{RUN}/own_cts', 'requires_artifacts': ['4_1_cts.odb']}, 'route': {'cmd': 'derive_timing_from_cts && route'}}}}
        normalized = cl.stage_list(job['spec'])
        with patch.object(cl, 'assumed_insertion') as assumed:
            self.assertFalse(cl.start_parallel_calibrate(job, normalized, normalized[0]))
        assumed.assert_not_called()
        self.assertEqual(job['stage_idx'], 0)

    def test_scalar_only_recipe_keeps_parallel_path(self):
        job = {'name': 'scalar', 'stage_idx': 0, 'spec': {'stages': {'route': {'cmd': 'route --insertion $CK_SS_MEAN'}}}}
        with patch.object(cl, 'assumed_insertion', return_value=(None, None)) as assumed:
            self.assertFalse(cl.start_parallel_calibrate(job, [], {'cmd': 'cts'}))
        assumed.assert_called_once_with(job)


if __name__ == '__main__':
    unittest.main()
