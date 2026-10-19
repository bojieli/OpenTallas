import tempfile
import unittest
from pathlib import Path
from xr_timing import QUALIFIED, XR_PATH, inject_cycles, check_run_source

class TimingTest(unittest.TestCase):
    def contract(self): return dict(xr_source_sha256=next(iter(QUALIFIED)), v_ctl_inject=7)
    def test_archived_program_retains_six(self): self.assertEqual(inject_cycles({}),6)
    def test_qualified_xr2_has_seven(self): self.assertEqual(inject_cycles({"timing_contract":self.contract()}),7)
    def test_wrong_latency_refused(self):
        c=self.contract();c["v_ctl_inject"]=6
        with self.assertRaises(ValueError): inject_cycles({"timing_contract":c})
    def test_simulator_source_must_match(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sources.sha256";c=self.contract()
            p.write_text(c["xr_source_sha256"]+"  src/"+XR_PATH+"\n");check_run_source(c,d)
            p.write_text("0"*64+"  src/"+XR_PATH+"\n")
            with self.assertRaises(ValueError): check_run_source(c,d)

if __name__ == "__main__": unittest.main()
