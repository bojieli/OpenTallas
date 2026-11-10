#!/usr/bin/env python3
"""TOK-VERIFY-1 11-10: compile_layers.sh hands the --bound-data bind to the LP model prep, and the prep refuses half a
bound-data selection (a bind without its manifest), so the prep never silently reads the legacy main-tree die top."""
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class BoundPrep(unittest.TestCase):
    def test_half_selection_refused(self):
        r = subprocess.run([sys.executable, str(HERE / 'prepare_frame_schedules.py'), '--tree', str(ROOT),
                            '--out', '/nonexistent/tv1', '--bound-data', '/nonexistent/bind'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('--bound-data needs --bound-data-manifest', r.stderr)

    def test_compile_layers_passes_bind_to_prep(self):
        sh = (HERE / 'compile_layers.sh').read_text()
        prep = [ln for ln in sh.splitlines() if 'prepare_frame_schedules.py' in ln and not ln.lstrip().startswith('#')]
        self.assertEqual(len(prep), 1)
        self.assertIn('"${prep_bd[@]}"', prep[0])
        self.assertIn('prep_bd=(--bound-data "$OT_BOUND_DATA" --bound-data-manifest', sh)


if __name__ == '__main__':
    unittest.main()
