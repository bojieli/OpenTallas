import unittest
from unittest import mock
import kit_wave as K


class TickVersion(unittest.TestCase):
    def test_current_source_keeps_launch_logic_enabled(self):
        ap = mock.Mock()
        self.assertTrue(K.scheduler_current(ap))
        ap.log.assert_not_called()

    def test_changed_loaded_code_reloads_in_the_same_tick(self):
        """KW-FIX-4 11-03: a changed scheduler re-runs the pass on the current code now (no deferral to the next tick)"""
        ap = mock.Mock()
        ap.DRY = False
        with mock.patch.object(K, 'IMPORTED_SCHEDULER_CODE', 'old-loaded-code'), \
                mock.patch.object(K.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout='', stderr='')) as run, \
                mock.patch.object(K, 'load_state', return_value={'items': {}}), mock.patch.dict(K.os.environ, {}):
            K.os.environ.pop('KW_RELOADED', None)
            self.assertEqual(K._step(ap, '/ap'), {'items': {}})
        ap.read_coord.assert_not_called()                  # the stale pass reads nothing and launches nothing
        cmd, env = run.call_args[0][0], run.call_args[1]['env']
        self.assertEqual(cmd[-1], 'step')
        self.assertEqual((env['KW_RELOADED'], env['KW_LOCK_HELD'], env['AP_DIR']), ('1', '1', '/ap'))
        self.assertIn('same tick', ap.log.call_args[0][0])

    def test_merge_mid_tick_cannot_create_new_attempt(self):
        ap = mock.Mock()
        state = {'items': {}}
        with mock.patch.object(K, 'IMPORTED_SCHEDULER_CODE', 'old-loaded-code'), mock.patch.dict(K.os.environ, {}):
            K.os.environ.pop('KW_RELOADED', None)
            self.assertIsNone(K.launch(ap, {}, state, 'hbm', {}, 'intel2'))
        self.assertEqual(state, {'items': {}})
        ap.launch_unit.assert_not_called()

    def test_reload_child_launches_with_its_code(self):
        with mock.patch.object(K, 'IMPORTED_SCHEDULER_CODE', 'old-loaded-code'), \
                mock.patch.dict(K.os.environ, {'KW_RELOADED': '1'}):
            self.assertTrue(K.scheduler_current(mock.Mock()))


if __name__ == '__main__':
    unittest.main()
