import unittest
from unittest import mock
import kit_wave as K

class TickVersion(unittest.TestCase):
    def test_current_source_keeps_launch_logic_enabled(self):
        ap=mock.Mock()
        self.assertTrue(K.scheduler_current(ap))
        ap.log.assert_not_called()
    def test_changed_loaded_code_defers_before_pending_release(self):
        ap=mock.Mock()
        with mock.patch.object(K,'IMPORTED_SCHEDULER_CODE','old-loaded-code'):
            self.assertIsNone(K._step(ap,None))
        ap.read_coord.assert_not_called()
        self.assertIn('next tick',ap.log.call_args[0][0])
    def test_merge_mid_tick_cannot_create_new_attempt(self):
        ap=mock.Mock(); state={'items':{}}
        with mock.patch.object(K,'IMPORTED_SCHEDULER_CODE','old-loaded-code'):
            self.assertIsNone(K.launch(ap,{},state,'hbm',{},'intel2'))
        self.assertEqual(state,{'items':{}})
        ap.launch_unit.assert_not_called()
if __name__=='__main__': unittest.main()
