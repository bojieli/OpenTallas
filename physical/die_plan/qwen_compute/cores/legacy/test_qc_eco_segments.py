import subprocess
import tempfile
import unittest
from pathlib import Path


class RouteSegments(unittest.TestCase):
    def run_hook(self, write=True, routes=True):
        with tempfile.TemporaryDirectory() as d:
            if write:
                (Path(d)/'eco_global_route.segments').write_text('actual saved segments')
            hook=Path(__file__).with_name('eco_pre_drt.tcl')
            s='set ::env(RESULTS_DIR) {'+d+'}\nnamespace eval grt {}\n'
            s+='proc read_global_route_segments {p} {puts "EXACT_READ $p"}\n'
            s+='proc grt::have_routes {} {return '+str(int(routes))+'}\n'
            s+='source {'+str(hook)+'}\n'
            return subprocess.run(['tclsh'],input=s,text=True,capture_output=True)

    def test_saved_exact_segments_restore(self):
        p=self.run_hook();self.assertIn('EXACT_READ',p.stdout);self.assertIn('restored exact',p.stdout);self.assertEqual(p.stderr,'')

    def test_missing_route_segments_fail_before_read(self):
        p=self.run_hook(write=False);self.assertIn('missing nonempty',p.stderr);self.assertNotIn('EXACT_READ',p.stdout)

    def test_unrestored_map_fails(self):
        p=self.run_hook(routes=False);self.assertIn('did not restore',p.stderr);self.assertNotIn('restored exact',p.stdout)


if __name__=='__main__':unittest.main()
