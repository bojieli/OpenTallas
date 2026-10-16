"""Actual placed-pin geometry must pass before gate/CTS evidence can qualify."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
import pre_route_gate as G
import fp_margin_lint as F


def fixture(rect=None):
    return dict(die=[0., 0., 10., 10.], layers=[dict(name='M2', level=2, dir='HORIZONTAL', width=.018, pitch=.036,
                track_patterns=[[.009, 278, .036]])],
                bterms=[['data[0]', 'n', 'SIGNAL', 'INPUT', [['M2', rect or [0., 0., .038, .018]]]]])


def remote_pin_block(dump):
    """Execute the real remote-shell validator block on a small actual JSON dump."""
    start = G.REMOTE_SH.index('# Validate the actual placed-IO dump')
    end = G.REMOTE_SH.index('# LAYOUT IMAGES', start)
    block = G.REMOTE_SH[start:end]
    with tempfile.TemporaryDirectory() as td:
        path = Path(td)
        (path / 'gate_dump.json').write_text(json.dumps(dump))
        script = 'set -uo pipefail\necho GATE_DUMP_RC=0\n' + block + '\necho CTS_WOULD_RUN\n'
        run = subprocess.run(['bash', '-c', script], cwd=ROOT, env=dict(os.environ, R=td, C=td),
                             capture_output=True, text=True, check=True)
        return run.stdout


def analyse(log):
    with tempfile.TemporaryDirectory() as td:
        kd = Path(td)
        (kd / 'floorplan.json').write_text(json.dumps(dict(die=[0, 0, 10, 10], blocks=[])))
        binding = dict(archive_sha256='a' * 64)
        out = 'GATE_SOURCE_ARCHIVE_SHA256=' + 'a' * 64 + '\nGATE_FLOW_RC=0 GATE_FLOW_S=1\nGATE_IOP_RC=0\n' + log
        gate = G.Gate()
        # Isolate actual-pin acceptance from separate port-latency/clock-policy tests.
        with patch.object(G, 'check_port_latency'), patch.object(G, 'clock_item'):
            G.analyse_remote(gate, kd, dict(kind='tile', route={}), out, False, binding, 10, 'fixture-host')
        return gate


class ActualPinGeometry(unittest.TestCase):
    def test_valid_actual_dump_passes_and_can_continue_to_cts(self):
        log = remote_pin_block(fixture())
        self.assertIn('CTS_WOULD_RUN', log)
        self.assertIn('GATE_PIN_GEOMETRY_RC=0', log)
        self.assertEqual(analyse(log).verdict, 'PASS')

    def test_old_gate_accepted_outside_pin_new_gate_refuses_before_cts(self):
        dump = fixture([10.001, 0., 10.039, .018])  # off-die along the non-track axis
        self.assertEqual(F.pin_track_access(dump), (1, []))
        log = remote_pin_block(dump)
        with patch.object(G, 'check_actual_pin_geometry'):
            self.assertEqual(analyse(log).verdict, 'PASS')  # exact prior parser behavior
        gate = analyse(log)
        self.assertEqual(gate.verdict, 'FAIL')
        self.assertTrue(any(i['check'] == 'floorplan.pin_bounds' for i in gate.items))
        self.assertNotIn('CTS_WOULD_RUN', log)

    def test_finite_tracks_and_minimum_landing_retained(self):
        for rect in ([0., 10., .038, 10.018], [0., 0., .038, .017]):
            with self.subTest(rect=rect):
                rep = F.pin_geometry(fixture(rect), require_tracks=True)
                self.assertTrue(any(f['check'] == 'pin_track' for f in rep['fails']))
                self.assertEqual(analyse(remote_pin_block(fixture(rect))).verdict, 'FAIL')

    def test_one_valid_shape_does_not_excuse_another_outside_die(self):
        dump = fixture()
        dump['bterms'][0][4].append(['M2', [10.001, 0., 10.039, .018]])
        self.assertEqual(F.pin_track_access(dump), (1, []))
        rep = F.pin_geometry(dump, require_tracks=True)
        self.assertEqual(rep['metrics']['pin_rectangles_outside'], 1)
        self.assertEqual(rep['verdict'], 'FAIL')

    def test_missing_tracks_and_nonfinite_shape_fail_closed(self):
        missing = fixture()
        del missing['layers'][0]['track_patterns']
        self.assertEqual(analyse(remote_pin_block(missing)).verdict, 'FAIL')
        invalid = fixture([0., 0., float('nan'), .018])
        log = remote_pin_block(invalid)
        self.assertIn('GATE_PIN_GEOMETRY_RC=2', log)
        self.assertEqual(analyse(log).verdict, 'FAIL')

    def test_absent_old_report_dump_failure_and_bad_result_never_pass(self):
        valid = remote_pin_block(fixture())
        cases = ['', valid.replace('GATE_DUMP_RC=0', 'GATE_DUMP_RC=1'),
                 valid.replace('GATE_PIN_GEOMETRY_RC=0', 'GATE_PIN_GEOMETRY_RC=2'),
                 valid + next(line for line in valid.splitlines() if line.startswith('GATE_PIN_GEOMETRY_RESULT ')) + '\n',
                 'GATE_DUMP_RC=0\nGATE_PIN_GEOMETRY_RC=0\nGATE_PIN_GEOMETRY_RESULT []\n']
        record = json.loads(next(line.split(' ', 1)[1] for line in valid.splitlines()
                                 if line.startswith('GATE_PIN_GEOMETRY_RESULT ')))
        wrong_findings = copy.deepcopy(record)
        wrong_findings['fails'] = ''
        cases.append('GATE_DUMP_RC=0\nGATE_PIN_GEOMETRY_RC=0\nGATE_PIN_GEOMETRY_RESULT ' + json.dumps(wrong_findings) + '\n')
        for key, value in [('pin_rectangles_outside', 1), ('pin_track_checked', 0)]:
            wrong = copy.deepcopy(record)
            wrong['metrics'][key] = value
            cases.append('GATE_DUMP_RC=0\nGATE_PIN_GEOMETRY_RC=0\nGATE_PIN_GEOMETRY_RESULT ' + json.dumps(wrong) + '\n')
        for log in cases:
            with self.subTest(log=log[:150]):
                self.assertEqual(analyse(log).verdict, 'FAIL')

    def test_route_checker_reuses_same_geometry_policy(self):
        dump = fixture([10.001, 0., 10.039, .018])
        dump.update(core=[0, 0, 10, 10], masters={}, macros=[], net_terms={}, pdn_edge=[], rows=[], blockages=[])
        rep = F.lint(dump)
        self.assertTrue(any(f['check'] == 'pin_bounds' for f in rep['fails']))
        self.assertEqual(rep['thresholds'], F.THRESHOLDS)



if __name__ == '__main__':
    unittest.main()
