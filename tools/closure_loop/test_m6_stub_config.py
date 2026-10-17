import tempfile
import unittest
from pathlib import Path
from m6_stub_config import depth

class M6StubConfig(unittest.TestCase):
    def test_nested_resume_hook_and_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'hooks').mkdir()
            c = p/'config.mk'
            c.write_text('export MAX_ROUTING_LAYER = M6\nexport PRE_GLOBAL_ROUTE_TCL = /work/hooks/resume.tcl\nexport POST_DETAIL_ROUTE_TCL = /work/hooks/post.tcl\n')
            (p/'hooks/resume.tcl').write_text('source /work/hooks/pre.tcl\nsource /src/physical/qwen_die_masters/pre_ref_skew.tcl\n')
            (p/'hooks/pre.tcl').write_text('set ::ot_m6_stub_um 0.384\nsource /src/physical/common_flow/m6_pin_access.tcl\n')
            (p/'hooks/post.tcl').write_text((p/'hooks/pre.tcl').read_text())
            self.assertEqual(depth(c), '0.384')
            (p/'hooks/post.tcl').write_text((p/'hooks/pre.tcl').read_text().replace('0.384','0.5'))
            with self.assertRaises(ValueError): depth(c)
            (p/'hooks/post.tcl').unlink()
            with self.assertRaises(ValueError): depth(c)

    def test_no_stub(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'config.mk'
            p.write_text('export MAX_ROUTING_LAYER = M5\n')
            self.assertEqual(depth(p), '')

if __name__ == '__main__': unittest.main()
