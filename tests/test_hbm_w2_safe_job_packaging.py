"""Validate W2 calibration packaging without launching tools or changing the loop."""
import json
from pathlib import Path
import shlex
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'physical/hbm_w2_safe_packaging_20261006'
RAW = ROOT / 'results/physical/hbm_bounded_harvest_20261006/raw'


def command_args(spec, stage):
    command = spec['stages'][stage]['cmd']
    for key, value in {'RUN': '/tmp/test-run', 'NAME': spec['name']}.items():
        command = command.replace('{' + key + '}', value)
    subprocess.run(['bash', '-n'], input=command, text=True, check=True)
    return shlex.split(command)


def value(args, flag):
    return args[args.index(flag) + 1]


class PackagingTest(unittest.TestCase):
    def test_calibration_uses_separate_cts_directory_matching_base(self):
        for n in (2, 3):
            with self.subTest(no=n):
                spec = json.loads((PACKAGE / f'no{n}.json').read_text())
                cal, route = (command_args(spec, s) for s in ('calibrate', 'route'))
                self.assertEqual(value(cal, '--run'), value(route, '--run') + '_cal')
                self.assertEqual(value(cal, '--pnr-stop-after'), 'cts')
                self.assertNotIn('--pnr-stop-after', route)
                base = spec['stages']['calibrate']['base'].replace('{RUN}', '/tmp/test-run').replace('{NAME}', spec['name'])
                self.assertTrue(base.startswith(value(cal, '--run') + '/'))

    def test_original_reproduces_packaging_defect(self):
        for n in (2, 3):
            original = json.loads((RAW / f'w2-no{n}-original-job.json').read_text())
            cal, route = (command_args(original, s) for s in ('calibrate', 'route'))
            self.assertEqual(value(cal, '--run'), value(route, '--run'))
            self.assertNotIn('--pnr-stop-after', cal)
            self.assertIn('{NAME}_cal/', original['stages']['calibrate']['base'])

    def test_physical_and_numerical_contracts_unchanged(self):
        for n in (2, 3):
            spec = json.loads((PACKAGE / f'no{n}.json').read_text())
            original = json.loads((RAW / f'w2-no{n}-original-job.json').read_text())
            for field in ('source', 'block', 'hosts', 'threads', 'peak_ram_gb', 'verdict', 'cycles_added'):
                self.assertEqual(spec[field], original[field])
            for stage in ('bench', 'route', 'signoff', 'collect'):
                self.assertEqual(spec['stages'][stage], original['stages'][stage])
            self.assertIsNone(spec['merge_target'])
            self.assertNotEqual(spec['record'][0]['to'], original['record'][0]['to'])

if __name__ == '__main__':
    unittest.main()
