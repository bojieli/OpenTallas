"""HEAD hd_serdes CDC packet (head_serdes_cdc.py): the admitted shell and its mutants (DIE-HEAD-9 2026-10-28).

Positive: ot_s81hd_serdes_cdc is admitted by the reviewed_gray_fifos engine with exactly one reviewed FIFO
(ot_s81_rate_match, serdes -> core, wptr/rptr 4 b + flt 1 b, 4096 storage bits, r_d proved gated by the 'gray_bin'
read-valid), two rule-(d) level synchronisers (lock, unc) and two rule-(c) reset pipes; the SDC has no false path /
clock group / multicycle.  Mutants: logic in a sync stage, unsynchronised port, metastable stage consumed, a
pma_rck data register outside the FIFO reaching clk, inline reset pipe, missing level declaration, 1-stage level,
ungated storage read (engine proof, fingerprint lifted), binary pointer publication (fingerprint).
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import head_serdes_cdc as H

G, C = H.G, H.C
YOSYS = Path(H.G._yosys()) if hasattr(H.G, '_yosys') else None
RM = H.G.REVIEWED['ot_s81_rate_match']['path']


def _have_tools():
    try:
        return Path(G._yosys()).exists()
    except Exception:
        return False


@unittest.skipUnless(_have_tools(), 'Yosys 0.68 required')
class HeadSerdesCdc(unittest.TestCase):
    def test_admitted(self):
        r = G.lint(H.spec(), H.ROOT)
        self.assertEqual({k: (f['module'], f['writer'], f['reader'], f['chains'], f['storage_bits'], f['storage_read'])
                          for k, f in r['fifos'].items()},
                         dict(f0=('ot_s81_rate_match', 'serdes', 'core', dict(wptr=4, rptr=4, flt=1), 4096, True)))
        self.assertEqual(sorted((l['name'], l['src'], l['dst'], l['stages']) for l in r['levels'].values()),
                         [('lock', 'serdes', 'core', 2), ('unc', 'serdes', 'core', 2)])
        self.assertEqual(sorted((x['scope'], x['domain']) for x in r['resets']), [('u_rs_r', 'serdes'), ('u_rs_t', 'core')])
        self.assertEqual(r['roles']['u_rm.r_d[7]'][0], 'consumer')
        text = C.generate(H.spec(), H.ROOT)
        for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
            self.assertNotIn(banned, text)

    def test_rtl_mutants_refused(self):
        for mut, why in [(1, 'level synchroniser lock stage 2 .* not a direct flop'),
                         (2, 'level synchroniser lock: source and every stage must be one actual flop bit'),
                         (3, r'lk_s\[1\] is not a single flop Q'),
                         (4, r'unapproved crossing q_v_r \(serdes\) -> rx\[0\]'),
                         (6, 'reset synchroniser u_rs_r has fewer than 2 stages')]:
            with self.subTest(mut=mut), self.assertRaisesRegex(G.GrayFifoError, why):
                G.lint(H.spec(mut), H.ROOT)

    def test_spec_mutants_refused(self):
        with self.assertRaisesRegex(G.GrayFifoError, r'unapproved crossing lock_r \(serdes\) -> lk_s\[0\]'):
            G.lint(H.spec(levels=[dict(name='unc', source='unc_r', chain=['uf_s[0]', 'uf_s[1]'])]), H.ROOT)
        with self.assertRaisesRegex(G.GrayFifoError, 'needs >= 2 destination stages'):
            G.lint(H.spec(levels=[dict(name='lock', source='lock_r', chain=['lk_s[0]'])]), H.ROOT)

    def _mutated_root(self, old, new):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for f in H.SOURCES:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(H.ROOT / f, root / f)
        text = (root / RM).read_text()
        self.assertEqual(text.count(old), 1)
        (root / RM).write_text(text.replace(old, new))
        return root

    def test_source_mutants_refused(self):
        ungated = self._mutated_root("else r_d <= 512'd2;", "else r_d <= mem[rp[2:0]];")   # read while empty
        binary = self._mutated_root('wp_g <= (wp + 1\'b1) ^ ((wp + 1\'b1) >> 1);', 'wp_g <= wp + 1\'b1;')
        for root in (ungated, binary):                       # the fingerprint refuses any edited reviewed source
            with self.assertRaises(G.GrayFifoError):
                G.lint(H.spec(), root)
        # with the fingerprint lifted the exact storage proof (gray_bin read-valid) still refuses the ungated read
        patched = dict(G.REVIEWED)
        patched['ot_s81_rate_match'] = dict(G.REVIEWED['ot_s81_rate_match'], sha256=(
            __import__('hashlib').sha256((ungated / RM).read_bytes()).hexdigest(),))
        with mock.patch.dict(G.REVIEWED, patched), \
                self.assertRaisesRegex(G.GrayFifoError, 'storage .* while the FIFO read-valid is false|not gated'):
            G.lint(H.spec(), ungated)


if __name__ == '__main__':
    unittest.main()
