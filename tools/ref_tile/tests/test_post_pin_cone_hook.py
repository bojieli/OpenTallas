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

if __name__=='__main__':unittest.main()
