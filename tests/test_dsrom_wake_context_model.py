"""First-principles root/leaf source-equation checks; no HDL or timing execution."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('wake_context',ROOT/'tools/model_dsrom_wake_context.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class WakeContextTests(unittest.TestCase):
    def test_startup_free_capture_and_go_lookahead(self):
        events=[{}]*3+[{'go':True}]+[{}]*5
        old=M.controls(events,False);wake=M.controls(events,True);bad=M.controls(events,True,True)
        self.assertEqual((1,0),(old[3]['leaf_edge'],wake[3]['leaf_edge']))
        self.assertEqual(1,wake[3]['x_capture_edge']);self.assertTrue(old[4]['go_consumed']);self.assertTrue(wake[4]['go_consumed']);self.assertTrue(bad[4]['missed_go'])
    def test_drain_root_count_and_wake_extra_tail(self):
        e=[{}]*3+[{'go':True}]+[{'walk_busy':True}]*10+[{}]*140
        old=M.controls(e,False);wake=M.controls(e,True)
        lastold=max(x['cycle'] for x in old if x['leaf_edge']);lastwake=max(x['cycle'] for x in wake if x['leaf_edge'])
        self.assertEqual(13+127,lastold);self.assertEqual(lastold+1,lastwake)
    def test_reset_reopens_and_cancels_pending_go(self):
        e=[{'go':True},{'reset':True},{}]
        for mode in (False,True):
            r=M.controls(e,mode);self.assertEqual(1,r[1]['leaf_edge']);self.assertFalse(r[1]['go_consumed']);self.assertEqual(0,r[2]['go_e']);self.assertEqual(0,r[2]['drain_before'])
    def test_source_pinned_model_keeps_physical_join_open(self):
        d=M.model();self.assertEqual(6,len(d['source_pins']));self.assertEqual(8,len(d['leaf_roles']))
        self.assertFalse(d['minimum_timing_model']['physical_closure']);self.assertIsNone(d['minimum_timing_model']['ICG_ENA_setup_hold_arc_values'])
        self.assertIn('OPEN',d['source_join']['state']);self.assertFalse(any(d['claims'].values()))
if __name__=='__main__':unittest.main()
