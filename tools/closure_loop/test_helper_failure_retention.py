"""Helper refusal preserves evidence and does not reconsume a failed ECO."""
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import closure_loop as cl


def blocked(status='NEEDS_HUMAN'):
    return dict(name='capt-v3', status=status, host='ot-epyc1tb', run='/srv/capt-v3',
                spec=dict(block='capt'), reason='10 consecutive loop errors: FROZEN_HELPER_OVERLAY: effective route helper drift',
                errors=[], events=[], metrics=dict(ss_ps=49.91, ff_ps=19.18, drc=0), failed_checks=[])


class RetentionTests(unittest.TestCase):
    def test_positive_helper_block_kept_by_deep_bulk_and_fleet_manifest(self):
        j = blocked()
        with tempfile.TemporaryDirectory() as td, patch.object(cl, 'NEAR_MISS_JSON', Path(td)/'keep.json'), \
                patch.object(cl, 'closed_blocks', return_value={'capt'}), \
                patch.object(cl, 'release_source_index', return_value={}), \
                patch.object(cl, 'ssh') as ssh:
            cl.release_bulk([j])
            ssh.assert_not_called()
            self.assertEqual(json.loads(cl.NEAR_MISS_JSON.read_text())['jobs'][0]['reason'], 'helper provenance blocked')
            self.assertIsNone(cl.deep_release_mode(j, {'capt'}, {}))
        self.assertEqual(j['status'], 'NEEDS_HUMAN')
        self.assertNotIn('deep_released', j)

    def test_pending_unknown_physics_retained_but_design_verdict_not_relabelled(self):
        j = blocked('READY'); j.update(reason='explicit recovery queued', metrics={}, errors=['ValueError: FROZEN_HELPER_OVERLAY: missing bytes'])
        self.assertTrue(cl.helper_provenance_retained(j))
        j.update(status='NEEDS_RTL', reason='TT -341ps / FF -13ps')
        self.assertFalse(cl.helper_provenance_retained(j))
        j.update(status='CANCELLED', reason='owner retired candidate')
        self.assertFalse(cl.helper_provenance_retained(j))
        j.update(status='NEEDS_HUMAN', reason='route rc=1')
        self.assertFalse(cl.helper_provenance_retained(j))

    def test_completed_receipt_helper_failure_is_bounded_and_retained(self):
        j = blocked('ECO_RESULT')
        j.update(reason=None, errors=[], eco=dict(rc=9, result=dict(tt_ps=-10.45, ff_ps=8.35, drc=1)))
        def finish(x, status, reason, text):
            x.update(status=status, reason=reason)
        with patch.object(cl, 'job_lock', return_value=nullcontext()), patch.object(cl, 'load_job', return_value=j), \
                patch.object(cl, 'save_job'), patch.object(cl, 'is_transient', return_value=False), \
                patch.object(cl, 'step', side_effect=ValueError('FROZEN_HELPER_OVERLAY: original bytes missing')) as step, \
                patch.object(cl, 'finish', side_effect=finish), patch.object(cl, 'log'):
            for _ in range(11):
                cl.advance_job(j['name'], Mock())
            self.assertEqual(step.call_count,10)
        self.assertEqual(j['status'],'NEEDS_HUMAN')
        self.assertEqual(j['eco']['rc'],9)
        self.assertTrue(cl.helper_provenance_retained(j))
        self.assertFalse(cl.eco_passes(j['eco']['result'],9))

    def test_actual_q8e_rc9_failure_is_consumed_once_before_helper_refusal(self):
        # Actual q8e least-bad receipt: no clean pass and one DRC; never install it.
        res = dict(tt_ps=-10.45, ss_ps=-10.45, ff_ps=8.35, drc=1,
                   ss_sensitivity_ps=-341.61, cells_added=2785, errors=[], chosen='least_bad')
        j = dict(name='q8e', status='ECO', spec={}, host='ot-epyc1tb', run='/srv/q8e',
                 events=[], metrics=dict(ss_ps=-14.95, ff_ps=-13.06, drc=0),
                 eco=dict(kind='combo', out='/srv/q8e/cl/eco-combo1', pre=dict(ss_ps=-14.95, ff_ps=-13.06)))
        saved = []
        with patch.object(cl, 'stage_list', return_value=[]), patch.object(cl, 'bench_track', return_value=True), \
                patch.object(cl, 'cal_track'), patch.object(cl, 'poll_stage', return_value=('DONE',9)) as poll, \
                patch.object(cl, 'ssh', return_value=Mock(stdout=json.dumps(res))) as ssh, \
                patch.object(cl, 'save_job', side_effect=lambda x:saved.append(copy.deepcopy(x))), \
                patch.object(cl, 'ledger'), patch.object(cl, 'combo_hold_retry_eligible', return_value=False), \
                patch.object(cl, 'summarize_failure', side_effect=ValueError('FROZEN_HELPER_OVERLAY: missing bytes')) as summary, \
                patch.object(cl, 'launch_stage') as launch:
            for _ in range(3):
                with self.assertRaisesRegex(ValueError, 'FROZEN_HELPER_OVERLAY'):
                    cl.step(j, Mock())
            self.assertEqual(poll.call_count,1)
            self.assertEqual(ssh.call_count,1)
            self.assertEqual(summary.call_count,3)
            launch.assert_not_called()
        self.assertEqual(j['status'],'ECO_RESULT')
        self.assertEqual(j['eco']['rc'],9)
        self.assertEqual(j['eco']['result'],res)
        self.assertEqual(sum('ECO MISS' in e for e in j['events']),1)
        self.assertEqual(saved[0]['status'],'ECO_RESULT')
        self.assertFalse(cl.eco_passes(res,9))
        self.assertNotIn('installed',j['eco'])
        with patch.object(cl, 'stage_list', return_value=[]), patch.object(cl, 'bench_track', return_value=True), \
                patch.object(cl, 'cal_track'), patch.object(cl, 'combo_hold_retry_eligible', return_value=False), \
                patch.object(cl, 'summarize_failure', side_effect=lambda x,*a:x.update(status='SUMMARY') or True), \
                patch.object(cl, 'poll_stage') as poll:
            cl.step(j,Mock())
            poll.assert_not_called()
        self.assertEqual(j['status'],'SUMMARY')

if __name__ == '__main__': unittest.main()
