import os, subprocess, sys, tempfile, pathlib, unittest
H = pathlib.Path(__file__).resolve().parent


class RefGuard(unittest.TestCase):
    def test_names_paths_of_live_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            src = (H / 'ot_cleanup_refguard.py').read_text().replace("/srv/opentallas-scratch2/claude", t)
            lane = pathlib.Path(t, 'lane/run/b/B6gE/out'); lane.mkdir(parents=True)
            (lane / 'asbuilt_run.json').write_text('{"src": "/srv/opentallas-scratch2/claude/type-safe-4/s81p3/romq_rtl"}')
            s = pathlib.Path(t, 'ref.py'); s.write_text(src)
            out = pathlib.Path(t, 'refs.tsv')
            subprocess.run([sys.executable, '-I', str(s), str(out)], check=True, capture_output=True)
            self.assertIn('/srv/opentallas-scratch2/claude/type-safe-4/s81p3/romq_rtl', out.read_text())


if __name__ == '__main__':
    unittest.main()
