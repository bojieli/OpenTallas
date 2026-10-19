"""Pin anchors must be fixed before regional cone ownership is assigned."""
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT

class PostPinConeHook(unittest.TestCase):
    def test_order_and_source_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            (root/'partition.tcl').write_text('# test cone partition')
            s={'name':'fixture','kind':'tile','clock':'cts','recipe':2,
               'io_flop_at_pins':{'enabled':True}, 'inhold':True,'pins':{},'sources':[],'route':{},'macros':[],'children':[],
               'pin_hook_after_flops':['partition.tcl']}
            with patch.object(RT,'ROOT',root):
                h=RT.gen_pin_hooks(s)['pre_gpl.tcl']
                self.assertLess(h.index('io_flop_at_pins.tcl'),h.index('partition.tcl'))
                self.assertIn('partition.tcl', RT.referenced_paths(s,'fixture'))
    def test_flop_first_wrapper_and_unsafe_path(self):
        s={'recipe':4,'io_flop_at_pins':True,'pin_hook_after_flops':['../bad.tcl']}
        self.assertTrue(RT.pin_hook_wrapper(s))
        with self.assertRaisesRegex(RT.SpecError,'safe relative'):
            RT.gen_pin_hooks(s)


class PostStageAudit(unittest.TestCase):
    def test_audits_follow_completed_physical_stages_and_are_frozen(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            (root/'audit.tcl').write_text('# read-only physical assertion')
            s={'name':'fixture','kind':'tile','clock':'cts','recipe':1,
               'pins':{},'route':{},'sources':[],'macros':[],'children':[],
               'post_stage_audits':['audit.tcl']}
            with patch.object(RT,'ROOT',root):
                h=RT.gen_hooks(s,'fixture')
                for stage in ['post_cts.tcl','post_grt.tcl','post_drt.tcl','post_fill.tcl']:
                    self.assertTrue(h[stage].endswith('source /src/audit.tcl\n'))
                self.assertNotIn('audit.tcl',h['pre_cts.tcl'])
                self.assertIn('audit.tcl',RT.referenced_paths(s,'fixture'))
    def test_unsafe_audit_path_is_rejected(self):
        s={'name':'fixture','kind':'tile','clock':'cts','recipe':1,'pins':{},'route':{},
           'post_stage_audits':['../outside.tcl']}
        with self.assertRaisesRegex(RT.SpecError,'safe relative'):
            RT.gen_hooks(s,'fixture')

if __name__=='__main__':unittest.main()
