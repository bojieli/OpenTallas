#!/usr/bin/env python3
"""Pair vE delta on a small plan: four views, four taps beside the transformed clk pin, nothing else moves."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 's81_head'))
import head_lep_pair_ve_delta as D  # noqa: E402

ORG = (([881.28, 17.28], 'MX'), ([69.12, 665.28], 'R0'), ([69.12, 17.28], 'MX'), ([881.28, 665.28], 'MY'))


def plan():
    cores = [dict(inst=f'u_core.u.g_pp[{i}].u_pair', module=D.MODULE, origin_um=o, orient=r, outline_um=[777.6, 492.48],
                  note='n') for i, (o, r) in enumerate(ORG)]
    return {'die': {'name': 's81_head'}, 'partition_types': {
        D.TYPE: {'outline_um': [1762.56, 1226.88], 'hard_cores': cores, 'clock': {'insertion_ps': 450.0}},
        'other': {'clock': {}}}}


class T(unittest.TestCase):
    def test_apply(self):
        p = plan()
        out = D.apply(p, ROOT)
        t = out['partition_types'][D.TYPE]
        self.assertEqual(t['clock']['core_taps'], 'early')
        self.assertEqual(t['clock']['insertion_ps'], 450.0)
        self.assertEqual(out['partition_types']['other'], p['partition_types']['other'])
        for x in t['clock']['taps']:
            self.assertAlmostEqual(x['insertion_ps'], 529.22, places=2)
            self.assertEqual(x['kind'], 'core')
            want = D.EXPECT[x['name'].rsplit('.', 1)[0]]
            self.assertAlmostEqual(x['xy'][0], want[0], delta=50.0)
            self.assertAlmostEqual(x['xy'][1], want[1], delta=50.0)
        for c in t['hard_cores']:
            self.assertEqual(c['lef'], D.VIEW + '.lef')
            self.assertIn('12.8a', c['note'])

    def test_refuses_existing_taps(self):
        p = plan()
        p['partition_types'][D.TYPE]['clock']['taps'] = [{}]
        with self.assertRaises(ValueError):
            D.apply(p, ROOT)


if __name__ == '__main__':
    unittest.main()
