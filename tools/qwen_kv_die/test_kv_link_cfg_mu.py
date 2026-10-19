#!/usr/bin/env python3
"""KV-LINKCFG-MU 2026-10-19: boot target 11 (the KV link end's calendar cfg, kv_static_programme.link_cfg_words) must be the
BOUND sequencer image's K calendar word for word: d2d_cal_image_mu.svh under OT_KV_MU=1 (MU context slot: K TX +1 entry,
TX SEG2 9), d2d_cal_image.svh otherwise.  The die seam stages come from the image's own record (the strict-bind source),
never from a constant in kv_static_programme.  Mutants: the pre-fix compile (old seam 2,2,2,2,2,2/11,11,9,9,9,11,11, no
--mu) and the non-MU compile against the MU image must both be refused by link_image_check.

    python3 tools/qwen_kv_die/test_kv_link_cfg_mu.py      (repository root; also collected by pytest)
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = 'rtl/qwen_sys/d2d_static_20261015/'
PROBE = r'''
import json, sys, tempfile
sys.path.insert(0, 'tools/qwen_kv_die')
import kv_static_programme as P
from pathlib import Path
over = json.loads(sys.argv[1])
if over.get('stages'):
    i = P.LINK_ARGS.index('--die-stages'); P.LINK_ARGS[i + 1] = over['stages']
if over.get('codec') is not None:
    i = P.LINK_ARGS.index('--kv-codec'); P.LINK_ARGS[i + 1] = str(over['codec'])
if over.get('drop_mu') and '--mu' in P.LINK_ARGS:
    P.LINK_ARGS.remove('--mu')
td = tempfile.mkdtemp()
cal = P.link_calendar(td)
w = P.link_cfg_words(Path(td) / 'cal')
out = dict(image=P.LINK_IMAGE, args=P.LINK_ARGS, words=w, want=P.image_link_cfg_words())
try:
    out['check'] = P.link_image_check(w, cal)
except ValueError as e:
    out['refused'] = str(e)
print('PROBE ' + json.dumps(out))
'''


def probe(mu, **over):
    env = dict(os.environ, OT_KV_MU='1' if mu else '0')
    p = subprocess.run([sys.executable, '-c', PROBE, json.dumps(over)], cwd=ROOT, env=env, capture_output=True, text=True,
                       timeout=600)
    line = [x for x in p.stdout.splitlines() if x.startswith('PROBE ')]
    assert p.returncode == 0 and line, p.stderr[-2000:]
    return json.loads(line[-1][6:])


class LinkCfgMu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mu, cls.su = probe(True), probe(False)

    def test_mu_target11_is_the_mu_image(self):
        r = self.mu
        self.assertEqual(r['image'], D + 'd2d_cal_image_mu.svh')
        self.assertIn('--mu', r['args'])
        self.assertTrue(r.get('check', {}).get('equal'), r.get('refused'))
        self.assertEqual(r['words'], r['want'])
        self.assertEqual(r['words'][64], 9)          # K TX SEG2: the MU slot moves the admission base 8 -> 9

    def test_su_target11_is_the_production_image(self):
        r = self.su
        self.assertEqual(r['image'], D + 'd2d_cal_image.svh')
        self.assertNotIn('--mu', r['args'])
        self.assertTrue(r.get('check', {}).get('equal'), r.get('refused'))
        self.assertEqual(r['words'][64], 8)

    def test_codec2_txdp_matches_both_images(self):
        for r in (self.mu, self.su):
            self.assertTrue(r['check']['txdp_k_agree'])
            self.assertEqual(r['check']['kv_codec'], 2)
            self.assertEqual(r['check']['txdp_k_image'], 0x03030416)

    def test_mutant_codec1_refused_even_with_equal_k_words(self):
        r = probe(True, codec=1)
        self.assertEqual(r['words'], r['want'])
        self.assertIn('TXDP codec differs', r['refused'])

    def test_mu_slot_present_only_in_mu(self):
        d = [i for i, (a, b) in enumerate(zip(self.mu['words'], self.su['words'])) if a != b]
        self.assertTrue(d, 'MU and single-user target 11 identical: the MU context slot is missing')

    def test_seam_is_the_images_record(self):
        for r in (self.mu, self.su):
            st = r['args'][r['args'].index('--die-stages') + 1]
            self.assertEqual(st, r['check']['die_stages'])
            self.assertNotEqual(st, '2,2,2,2,2,2/11,11,9,9,9,11,11')   # the stale pre-MU seam constant is gone

    def test_mutant_prefix_compile_refused(self):
        # the compile target 11 used before this fix: old seam, no --mu, checked against the MU image
        r = probe(True, stages='2,2,2,2,2,2/11,11,9,9,9,11,11', drop_mu=True)
        self.assertIn('refused', r)
        self.assertIn('differs from', r['refused'])

    def test_mutant_no_mu_against_mu_image_refused(self):
        r = probe(True, drop_mu=True)
        self.assertIn('refused', r)


if __name__ == '__main__':
    unittest.main(verbosity=2)
