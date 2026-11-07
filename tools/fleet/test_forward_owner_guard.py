"""Bounded forward-input opt-in; dead-client result recovery stays intact."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('forward_guard_test', str(Path(__file__).with_name('ot-run')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class ForwardOwnerGuard(unittest.TestCase):
    def setUp(self):
        self.owner = dict(pid=123, boot_id='boot', start_ticks='100', state='S')

    def test_same_live_owner_not_held(self):
        self.assertEqual(m.forward_owner_hold(self.owner, dict(self.owner)), '')

    def test_missing_dead_and_reused_identity_need_review_not_cancel(self):
        for current in [None, dict(self.owner, start_ticks='200'), dict(self.owner, boot_id='newboot')]:
            self.assertIn('not cancellation', m.forward_owner_hold(self.owner, current))
        self.assertIn('review required', m.forward_owner_hold(None, self.owner))

    def test_stopped_owner_is_held(self):
        for state in ['T', 't', 'Z', 'X']:
            self.assertIn('review required', m.forward_owner_hold(self.owner, dict(self.owner, state=state)))

    def test_only_explicit_intent_for_exact_incarnation_applies(self):
        for intent in ['STOP', 'HOLD']:
            self.assertIn('explicit forward', m.forward_owner_hold(self.owner, self.owner, dict(self.owner, intent=intent)))
        wrong = dict(self.owner, start_ticks='old', intent='STOP')
        self.assertEqual(m.forward_owner_hold(self.owner, self.owner, wrong), '')
        self.assertEqual(m.forward_owner_hold(self.owner, self.owner, dict(self.owner, intent='CANCEL')), '')

    def test_legacy_default_does_not_probe_or_hold(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(m, 'process_identity', side_effect=AssertionError('must not probe')):
            self.assertEqual(m.forward_owner_guard(None), '')

    def test_forward_hold_starts_no_copy_or_pending_record(self):
        with patch.object(m, 'forward_owner_guard', return_value='explicit forward STOP'), \
             patch.object(m, 'spill_copy_fwd') as copy, patch.object(m, 'pending_write') as write:
            self.assertIsNone(m.spill_run('src', 'dst', ['/kit'], 1, 20, ['run'], '/kit', None, lambda x: None))
            copy.assert_not_called()
            write.assert_not_called()

    def test_dead_client_backcopy_still_recovers_despite_opt_in_stop_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'legacy.json'
            rec = dict(tag='legacy', pid=123, src='src', dst='dst', roots=['/kit'], stamp='/stamp', unit=None)
            path.write_text(json.dumps(rec))
            with patch.object(m, 'SPILL_PENDING', tmp), patch.object(m, 'pid_alive', return_value=False), \
                 patch.object(m, 'spill_copy_back', return_value=(True, '')) as copy, \
                 patch.dict(os.environ, {'OT_RUN_FORWARD_OWNER_GUARD':'1', 'OT_RUN_FORWARD_HOLD_FILE':'/unreadable'}):
                self.assertEqual(m.spill_sweep(say=lambda x: None), 0)
                copy.assert_called_once_with('src', 'dst', ['/kit'], '/stamp', only=None)
            self.assertTrue(Path(tmp, 'legacy.done').exists())


if __name__ == '__main__':
    unittest.main()
