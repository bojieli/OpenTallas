#!/usr/bin/env python3
"""tools/die_reach.py + the die generators that emit repair_design (python3 tools/test_die_reach.py)."""
import argparse
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_reach  # noqa: E402

GENERATORS = {'tools/hbm_die_v15/die_case.py': 'hbm', 'tools/hbm_die_v15/die_case_v16.py': 'hbm',
              'tools/qwen_die_drt_pilot.py': 'qwen_compute'}


def parse(design, argv):
    ap = argparse.ArgumentParser()
    die_reach.add_args(ap, design)
    return die_reach.from_args(ap.parse_args(argv), design)


class DieReach(unittest.TestCase):
    def test_table_values(self):
        self.assertEqual(die_reach.reach_um('hbm'), 450.0)
        self.assertEqual(die_reach.reach_um('s81'), 455.0)
        self.assertEqual(die_reach.reach_um('qwen_compute'), 425.0)
        self.assertEqual(die_reach.reach_um('qwen_kv'), 446.0)
        for d in ('hbm', 's81', 'qwen_compute', 'qwen_kv'):
            r = die_reach.record(d)
            self.assertTrue(r['method'] and r['evidence'], d)
            lo, hi = r['measured_range_um']
            self.assertLessEqual(r['reach_um'], hi, d)

    def test_missing_design_fails_closed(self):
        with self.assertRaises(die_reach.DieReachError):
            die_reach.reach_um('no_such_die')
        with tempfile.TemporaryDirectory() as t:
            os.environ['OT_DIE_REACH'] = str(Path(t) / 'absent.json')
            try:
                with self.assertRaises(die_reach.DieReachError):
                    die_reach.reach_um('hbm')
            finally:
                del os.environ['OT_DIE_REACH']

    def test_default_is_reach(self):
        mw = parse('hbm', [])
        self.assertEqual((mw['value_um'], mw['reach_um'], mw['over_reach_reason']), (450.0, 450.0, None))
        self.assertEqual(mw['source'], 'results/arch/die_reach_1016.json')

    def test_below_reach_ok(self):
        self.assertEqual(parse('hbm', ['--max-wire-um', '400'])['value_um'], 400.0)

    def test_over_reach_refused(self):
        with self.assertRaises(SystemExit) as e:
            parse('hbm', ['--max-wire-um', '451'])
        self.assertIn('exceeds the measured hbm die reach 450', str(e.exception))
        with self.assertRaises(SystemExit):
            parse('qwen_compute', ['--max-wire-um', '430'])          # the old literal is now over reach
        with self.assertRaises(SystemExit):
            parse('hbm', ['--max-wire-um', '500', '--allow-over-reach', '  '])
        with self.assertRaises(SystemExit):
            parse('hbm', ['--max-wire-um', '0'])

    def test_over_reach_with_reason(self):
        mw = parse('hbm', ['--max-wire-um', '500', '--allow-over-reach', 'M8/M9 long-reach study'])
        self.assertEqual((mw['value_um'], mw['over_reach_reason']), (500.0, 'M8/M9 long-reach study'))

    def test_repair_tcl(self):
        self.assertEqual(die_reach.repair_tcl(parse('hbm', []), '-buffer_gain 4.0'),
                         'repair_design -max_wire_length 450 -buffer_gain 4.0')
        self.assertEqual(die_reach.repair_tcl(437.5), 'repair_design -max_wire_length 437.5')


class Generators(unittest.TestCase):
    def test_no_literal_max_wire(self):
        root = HERE.parent
        for g, design in GENERATORS.items():
            src = (root / g).read_text()
            self.assertIsNone(re.search(r'max_wire_length\s+\d', src), g)
            self.assertIn('die_reach.repair_tcl(', src, g)
            self.assertIn(f"die_reach.add_args(ap, {design!r}" if g.endswith('die_case.py') or g.endswith('v16.py')
                          else 'die_reach.add_args(ap, DESIGN)', src, g)

    def test_qwen_pilot_tcl(self):
        import qwen_die_drt_pilot as Q
        self.assertIn('repair_design -max_wire_length 425 -verbose', Q.pilot_tcl(8, 'x'))
        self.assertIn('repair_design -max_wire_length 400 -verbose', Q.pilot_tcl(8, 'x', die_reach.resolve('qwen_compute', 400)))
        with tempfile.TemporaryDirectory() as t:
            Q.main(['--case', t, '--threads', '4'])
            self.assertIn('-max_wire_length 425 ', (Path(t) / 'pilot.tcl').read_text())
            self.assertEqual(json.loads((Path(t) / 'max_wire.json').read_text())['value_um'], 425.0)
            with self.assertRaises(SystemExit):
                Q.main(['--case', t, '--max-wire-um', '430'])
            Q.main(['--case', t, '--max-wire-um', '430', '--allow-over-reach', 'old SS corridor pitch replay'])
            self.assertIn('-max_wire_length 430 ', (Path(t) / 'pilot.tcl').read_text())

    def test_hbm_die_case_arg_wiring(self):
        """die_case / die_case_v16 parse --max-wire-um before any input is read: an over-reach value exits first"""
        import subprocess
        for g in ('tools/hbm_die_v15/die_case.py', 'tools/hbm_die_v15/die_case_v16.py'):
            req = (['--out', '/nonexistent/x', '--ctrl-view', 'x', '--feed-view', 'x', '--sm-view', 'x']
                   if g.endswith('die_case.py') else ['--views', '/nonexistent', '--out', '/nonexistent/x'])
            p = subprocess.run([sys.executable, str(HERE.parent / g), *req, '--max-wire-um', '460'],
                               capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0, g)
            self.assertIn('exceeds the measured hbm die reach 450', p.stderr, g)


if __name__ == '__main__':
    unittest.main()
