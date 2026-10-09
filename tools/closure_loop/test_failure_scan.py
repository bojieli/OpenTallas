"""Terminal geometry failures must enter the existing owner's failure queue."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class FailureScanTests(unittest.TestCase):
    def test_floorplan_failure_is_dispatched_and_processed_receipt_is_honored(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs = root / 'state' / 'jobs'
            jobs.mkdir(parents=True)
            takeover = root / 'takeover'
            event = '2026-10-08T22:54:59-07:00 FLOORPLAN_MARGIN: pin_density'
            job = dict(name='hbm_bad_geometry', status='FLOORPLAN_MARGIN',
                       spec={'block': 'geometry'}, host='test-host', events=[event])
            path = jobs / 'hbm_bad_geometry.json'
            path.write_text(json.dumps(job))
            env = dict(os.environ, CL_STATE=str(root / 'state'), CL_TAKEOVER=str(takeover))
            script = Path(__file__).with_name('failure_scan.py')
            subprocess.run([sys.executable, str(script)], env=env, check=True, capture_output=True)
            out = next((takeover / 'failtrig').glob('new_*.json'))
            record = json.loads(out.read_text())
            self.assertEqual(record['groups']['floorplan:hbm'][0]['job'], job['name'])
            self.assertEqual(json.loads(path.read_text()), job)
            subprocess.run([sys.executable, str(script), '--commit', str(out)],
                           env=env, check=True, capture_output=True)
            subprocess.run([sys.executable, str(script)], env=env, check=True, capture_output=True)
            self.assertEqual(json.loads(out.read_text())['names'], [])


if __name__ == '__main__':
    unittest.main()
