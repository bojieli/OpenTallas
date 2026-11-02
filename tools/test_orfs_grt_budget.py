import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('mm_budget',Path(__file__).with_name('orfs_hold_mm.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class Budget(unittest.TestCase):
 def test_actual_tcl_default_explicit_and_cugr(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'global_route.tcl';p.write_text('proc budget {use_cugr} {\n'+M.GRT_BUDGET_ANCHOR+'\n    if {$use_cugr ne ""} {set cong_iters "-congestion_iterations 10"}\n    return $cong_iters\n}\n')
   self.assertEqual(M.patch_grt_budget(Path(d)),'patched')
   self.assertEqual(M.patch_grt_budget(Path(d)),'already patched')
   script=f'source {{{p}}}\n'
   script+='if {[budget {}] ne "-congestion_iterations 30"} {error default}\n'
   script+='set ::env(GRT_OVERFLOW_ITERS) 50\nif {[budget {}] ne "-congestion_iterations 50"} {error requested}\n'
   script+='if {[budget cugr] ne "-congestion_iterations 10"} {error alternate_policy}\n'
   script+='set ::env(GLOBAL_ROUTE_ARGS) {-congestion_iterations 50 -verbose}\nif {[budget {}] ne ""} {error dedup_explicit}\n'
   script+='set ::env(GLOBAL_ROUTE_ARGS) {-verbose}\nif {[budget {}] ne "-congestion_iterations 50"} {error keep_default}\n'
   script+='unset ::env(GLOBAL_ROUTE_ARGS)\n'
   script+='set ::env(GRT_OVERFLOW_ITERS) 0\nif {![catch {budget {}}]} {error invalid_budget}\nputs PASS\n'
   r=subprocess.run(['tclsh'],input=script,capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertIn('PASS',r.stdout);self.assertFalse(r.stderr,r.stderr)
 def test_unknown_image_is_not_rewritten(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'global_route.tcl';p.write_text('global_route -congestion_iterations 50\n')
   self.assertIn('unchanged',M.patch_grt_budget(Path(d)))
   self.assertEqual(p.read_text(),'global_route -congestion_iterations 50\n')
if __name__=='__main__':unittest.main()
