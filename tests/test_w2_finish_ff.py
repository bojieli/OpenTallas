import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('finish_ff', ROOT/'physical/hbm_w2_rb_station_20261006/finish_ff.py')
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

class FinishFFTest(unittest.TestCase):
    def test_preconditions_prevent_hold_repair(self):
        for drc, ss_ok, ff_ok, expected in [(0, False, False, 'NEEDS_STRUCTURAL_SETUP_OR_DRC_FIX'),
                                           (2, True, False, 'NEEDS_STRUCTURAL_SETUP_OR_DRC_FIX'),
                                           (0, True, True, 'PASS_WITHOUT_ECO')]:
            with self.subTest(drc=drc, ss_ok=ss_ok, ff_ok=ff_ok), tempfile.TemporaryDirectory() as td:
                root = Path(td); route = root/'route'; out = root/'out'
                base = route/'work/orfs/results/asap7/dut/base'; base.mkdir(parents=True)
                for n in ('5_2_route.odb', '6_final.odb', '6_final.spef'):
                    (base/n).write_text('immutable fixture')
                (route/'station.sdc').write_text('strict fixture')
                logs = route/'work/orfs/logs/asap7/dut/base'; logs.mkdir(parents=True)
                (logs/'5_2_route.json').write_text(json.dumps({'detailedroute__route__drc_errors': drc}))
                pre = {'accept': {'SS_ok': ss_ok, 'FF_ok': ff_ok}, 'process_exit': 0 if ff_ok and ss_ok else 1}
                with patch('sys.argv', ['finish_ff.py', '--route', str(route), '--out', str(out)]), \
                     patch.object(F, 'evaluate', return_value=(pre, root/'strict.sdc')), \
                     patch.object(F.subprocess, 'run') as run:
                    F.main()
                    run.assert_not_called()
                self.assertEqual(json.loads((out/'result.json').read_text())['status'], expected)
                self.assertEqual((base/'5_2_route.odb').read_text(), 'immutable fixture')

if __name__ == '__main__':
    unittest.main()
