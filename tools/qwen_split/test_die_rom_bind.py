#!/usr/bin/env python3
"""tests for tools/qwen_split/die_rom_bind.py on synthetic die.v + the REAL qfd_c_b16_dv.sv / tile sources"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_rom_bind as R  # noqa: E402


def die(tmp: Path, cids, extra=''):
    lines = ['module qfd_die ();']
    for i, c in enumerate(cids):
        cv = c if isinstance(c, str) else f"12'h{c:x}"
        lines.append(f'  qfd_c_b16_dv c16_X{i} (.bc0(n_a), .cid({cv}), .far(1\'h0));')
    lines += [extra, 'endmodule']
    p = tmp / 'die.v'
    p.write_text('\n'.join(lines) + '\n')
    return p


class T(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_full_die_pass_and_strap_values(self):
        v, doc, vh = R.run(die(self.tmp, range(48)), ROOT, None, None, '`OT_ROM_BIND_TOP.', [], 0)
        self.assertEqual(v, 'PASS', doc['audit']['fails'])
        by = {b['path']: b['ROM_TILE'] for b in doc['tiles']}
        # XT1 (cid 1) hand binding: u_t_0_0 16, u_t_0_1 18, u_t_0_2 24, u_t_1_0 17, u_t_3_3 31
        self.assertEqual([by[f'c16_X1.{t}'] for t in ('u_t_0_0', 'u_t_0_1', 'u_t_0_2', 'u_t_1_0', 'u_t_3_3')],
                         [16, 18, 24, 17, 31])
        self.assertIn('defparam `OT_ROM_BIND_TOP.c16_X1.u_t_0_1.ROM_TILE = 18;', vh)
        self.assertEqual(doc['tiles'][0]['macros'][:3], ['qtile_t0_b0_c0', 'qtile_t0_b0_c1', 'qtile_t0_b1_c0'])
        self.assertEqual(doc['audit']['macros'], 7680)

    def test_nonconstant_cid_fails(self):
        v, doc, _ = R.run(die(self.tmp, list(range(47)) + ['n_cid_net']), ROOT, None, None, '', [], 0)
        self.assertEqual(v, 'FAIL')
        self.assertTrue(any('not a constant' in f for f in doc['audit']['fails']))

    def test_duplicate_cid_and_coverage_fail(self):
        v, doc, _ = R.run(die(self.tmp, list(range(47)) + [3]), ROOT, None, None, '', [], 0)
        self.assertEqual(v, 'FAIL')
        self.assertTrue(any('duplicate' in f for f in doc['audit']['fails']))

    def test_missing_cluster_fails(self):
        v, doc, _ = R.run(die(self.tmp, range(47)), ROOT, None, None, '', [], 0)
        self.assertEqual(v, 'FAIL')

    def test_only_prefix(self):
        v, doc, vh = R.run(die(self.tmp, range(48)), ROOT, None, None, '', ['c16_X1'], 0)
        self.assertEqual(v, 'PASS', doc['audit']['fails'])
        self.assertIn('defparam c16_X1.u_t_0_0.ROM_TILE = 16;', vh)
        self.assertEqual(len(doc['tiles']), 16)

    def test_broken_chain_fails(self):
        root = self.tmp / 'root'
        for d in R.SEARCH + ('rtl/physical/qcluster',):
            (root / d).mkdir(parents=True, exist_ok=True)
        for d in R.SEARCH:
            for f in (ROOT / d).glob('*.sv'):
                os.symlink(f, root / d / f.name)
        os.symlink(ROOT / R.CLUSTER_SRC, root / R.CLUSTER_SRC)
        f = root / 'rtl/physical/qfd_tile_nl_rp2_romleaf_rr.sv'
        txt = f.read_text().replace('.ROM_TILE(ROM_TILE),', '')
        f.unlink()
        f.write_text(txt)
        v, doc, _ = R.run(die(self.tmp, range(48)), root, None, None, '', [], 0)
        self.assertEqual(v, 'FAIL')
        self.assertFalse(doc['audit']['chain']['qfd_tile_nl_rp2_romleaf_rr']['ok'])
        self.assertTrue(doc['audit']['chain']['qfd_tile_nk_rp2_romleaf_rr']['ok'])

    def _manifest(self, tiles, corrupt=None, drop=None):
        md = self.tmp / 'rank0'
        (md / 'masks').mkdir(parents=True)
        pairs = []
        for t in tiles:
            for b in range(5):
                cols = []
                for c in range(2):
                    n = f'qtile_t{t}_b{b}_c{c}'
                    if n == drop:
                        continue
                    p = md / 'masks' / (n + '.viamap.hex')
                    p.write_text(f'{t:04x}{b}{c}\n')
                    h = hashlib.sha256(p.read_bytes()).hexdigest()
                    if n == corrupt:
                        p.write_text('00\n')
                    cols.append(dict(instance=n, file=p.name, sha256=h))
                pairs.append(dict(tile=t, bank=b, columns=cols))
        m = md / 'manifest.json'
        m.write_text(json.dumps(dict(schema='opentallas.qwen-tp8-native-code-mask-rank.v1', rank=0, pairs=pairs,
                                     partial_stages=list(range(2, 36)) + ['head'])))
        return m

    def test_masks_pass_and_fail(self):
        d = die(self.tmp, range(48))
        v, doc, _ = R.run(d, ROOT, self._manifest(range(16, 32)), 0, '', ['c16_X1'], 0)
        self.assertEqual(v, 'PASS', doc['audit']['fails'])
        self.assertEqual(doc['audit']['masks']['files_ok'], 160)
        self.assertEqual(doc['audit']['masks']['hashed'], 160)

    def test_masks_corrupt(self):
        v, doc, _ = R.run(die(self.tmp, range(48)), ROOT, self._manifest(range(16, 32), corrupt='qtile_t20_b3_c1'),
                          0, '', ['c16_X1'], 0)
        self.assertEqual(v, 'FAIL')
        self.assertTrue(any('sha256' in f for f in doc['audit']['fails']))

    def test_masks_missing_entry(self):
        v, doc, _ = R.run(die(self.tmp, range(48)), ROOT, self._manifest(range(16, 32), drop='qtile_t31_b4_c0'),
                          0, '', ['c16_X1'], 0)
        self.assertEqual(v, 'FAIL')
        self.assertTrue(any('lacks 1 of 160' in f for f in doc['audit']['fails']))


if __name__ == '__main__':
    unittest.main()
