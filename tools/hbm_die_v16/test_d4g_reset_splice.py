#!/usr/bin/env python3
"""Contract reset replacement must remove POR feeds and preserve every bit/bridge source."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_relay_splice as S


def contract():
    return dict(instances={'sink': {'ports': {'rst_n': {'bits': 2}}}},
                clock_resets=[dict(instance='sink', port='rst_n', bits=2, kind='reset',
                                   source=['hb_ckgen', 'por_stream'])], edges=[])


def layer():
    return dict(reset_forest_ports=[['sink', 'rst_n']], edges=[
        dict(src=['leaf', 'rst_n', 0, 1], dst=['sink', 'rst_n', b, b + 1]) for b in range(2)])


class ResetSplice(unittest.TestCase):
    def test_vector_reset_requires_every_bit(self):
        c, l, problems = contract(), layer(), []
        S.detach_reset_inputs(c, l, problems)
        self.assertEqual(problems, [])
        self.assertEqual(c['clock_resets'], [])
        c, l, problems = contract(), layer(), []
        l['edges'].pop()
        S.detach_reset_inputs(c, l, problems)
        self.assertIn('incomplete target', problems[0])

    def test_duplicate_reset_driver_is_refused(self):
        c, l, problems = contract(), layer(), []
        l['edges'].append(dict(l['edges'][0]))
        S.detach_reset_inputs(c, l, problems)
        self.assertTrue(any('duplicate drive' in p for p in problems))

    def test_stale_and_nonreset_drops_are_refused(self):
        c, l, problems = contract(), layer(), []
        l['reset_forest_ports'] = [['other', 'rst_n']]
        S.detach_reset_inputs(c, l, problems)
        self.assertIn('stale target', problems[0])
        c, l, problems = contract(), layer(), []
        c['edges'] = [dict(source=['source', 'data', 0, 1], sink=['sink', 'rst_n', 0, 1])]
        l['drop_edges'] = [['source', 'data', 'sink']]
        S.detach_reset_inputs(c, l, problems)
        self.assertTrue(any('refuses non-reset drop' in p for p in problems))
        self.assertEqual(len(c['edges']), 1)

    def test_cli_actual_reset_rtl(self):
        port = dict(clk=dict(bits=1, direction='input'), rst_n_in=dict(bits=1, direction='input'),
                    rst_n=dict(bits=1, direction='output'))
        c = dict(instances={'sink': dict(master='hbfd_rrl_hop', ports=port)}, masters={'hbfd_rrl_hop': 1},
                 edges=[], clock_resets=[dict(instance='sink', port='rst_n_in', bits=1, domain='stream',
                    kind='reset', source=['hb_ckgen', 'por_stream'])], straps=[], gaps=[], summary={})
        l = dict(region='reset_forest', instances=[dict(name='leaf', master='hbfd_rrl_hop',
            source='rtl/hbm_accel/die_glue/hbfd_rrl.sv', params={}, rtl_deps=['rtl/lib/ot_rst_relay.sv'])],
            reset_forest_ports=[['sink', 'rst_n_in']],
            edges=[dict(src=['leaf', 'rst_n'], dst=['sink', 'rst_n_in'], clock='stream')],
            clocks=[dict(inst='leaf', port='clk', kind='clock', domain='stream'),
                    dict(inst='leaf', port='rst_n_in', kind='reset', domain='stream')])
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, obj in [('c.json', c), ('l.json', l)]:
                (d / name).write_text(json.dumps(obj))
            r = subprocess.run([sys.executable, str(Path(S.__file__)), str(d/'c.json'), str(d/'l.json'),
                                str(d/'out.json'), '--report', str(d/'report.json')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = json.loads((d/'out.json').read_text())
            self.assertFalse(any(x['instance']=='sink' for x in out['clock_resets']))
            self.assertEqual(out['edges'][0]['sink'], ['sink', 'rst_n_in', 0, 1])
            self.assertEqual(out['edges'][0]['source'], ['leaf', 'rst_n', 0, 1])
            self.assertEqual(json.loads((d/'report.json').read_text())['problems'], [])


if __name__ == '__main__':
    unittest.main()
