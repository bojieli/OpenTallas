#!/usr/bin/env python3
"""--dedupe-pad kcopy (S-DIE-KCOPY 2026-10-16): generated k-copy netlist binds to the closed standards' RTL, the cut
nets keep every logical bit in order, and malformed maps are refused.  Simulation exactness: prove_dedupe_pad.py --kcopy
(run on the fleet; receipt results/arch/native_pin_audit_snetfill_1015/kcopy_proof_1016)."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81'))
MAP = ROOT / 'results/arch/tile_dedupe_1015/s81_pad_map_kcopy_1016.json'


def _mini(km, views, frm_ports, kind='hstn', name='u0', master=None, extra=None):
    """one FROM instance between a driver block 'a' and a load block 'b' (each port its own net)"""
    import dsrom_s81_fulldie as G
    G.bound_views = lambda: {t: dict(w=20.0, h=20.0, pins={(f'{p}[{b}]' if w > 1 else p): d.upper()
                                                         for p, (d, w) in ps.items() for b in range(w)})
                             for t, ps in views.items()}
    G.DIE = (2000.0, 2000.0)
    G.STN_FOOTPRINTS = {}
    G.DEDUPE_PAD = dict(path='t', map={}, kcopy=km)
    insts = [G.Inst(name, master or next(iter(km)), 500.0, 500.0, 30.0, 30.0, 'R0', kind=kind),
             G.Inst('a', 'blk_a', 100.0, 100.0, 20.0, 20.0), G.Inst('b', 'blk_b', 900.0, 900.0, 20.0, 20.0)]
    buses = []
    for p, (d, w) in frm_ports.items():
        buses.append((f'n_{p}', 'local', w, [('a', p), (name, p)] if d == 'input' else [(name, p), ('b', p)]))
    m = dict(insts=insts, buses=buses, glue=extra or {})
    G._dedupe_kcopy(m, km)
    return G, m


class KcopyUnit(unittest.TestCase):
    VIEWS = {'dsfd_hstnv_6': {'ck': ('input', 1), 'di': ('input', 6), 'dq': ('output', 6)}}
    KM = {'dsfd_hstnv_10': dict(stack='x', copies=[
        dict(to='dsfd_hstnv_6', ports=dict(di=[['di', 0, 5]], dq=[['dq', 0, 5]])),
        dict(to='dsfd_hstnv_6', ports=dict(di=[['di', 6, 9]], dq=[['dq', 6, 9]]))])}
    FROM = {'ck': ('input', 1), 'di': ('input', 10), 'dq': ('output', 10)}

    def test_split_cuts_and_pads(self):
        G, m = _mini(self.KM, self.VIEWS, self.FROM)
        names = sorted(it.name for it in m['insts'])
        self.assertEqual(names, ['a', 'b', 'u0__k0', 'u0__k1'])
        k0, k1 = (next(it for it in m['insts'] if it.name == n) for n in ('u0__k0', 'u0__k1'))
        self.assertEqual((k0.master, k1.master), ('dsfd_hstnv_6', 'dsfd_hstnv_6'))
        self.assertAlmostEqual(k0.y, k1.y)                 # side by side along x (hstnv data faces N/S)
        self.assertGreater(k1.x, k0.x + k0.w - 1e-6)
        eps = {b[0]: b[3] for b in m['buses']}
        self.assertEqual(eps['n_di'], [('a', 'di[0:5]'), ('u0__k0', 'di')])
        self.assertEqual(eps['n_di__kc6'], [('a', 'di[6:9]'), ('u0__k1', 'di')])
        self.assertEqual(eps['n_dq__kc6'], [('u0__k1', 'dq'), ('b', 'dq[6:9]')])
        self.assertEqual(eps['n_ck'], [('a', 'ck'), ('u0__k0', 'ck'), ('u0__k1', 'ck')])   # one ck sink per copy
        self.assertEqual(m['pad']['u0__k1']['ports'], {'di': 4, 'dq': 4})
        self.assertNotIn('u0__k0', m['pad'])
        self.assertEqual(m['kcopy']['by_master'], {'dsfd_hstnv_10': 1})

    def test_unmapped_output_bit_refused(self):
        km = json.loads(json.dumps(self.KM))
        km['dsfd_hstnv_10']['copies'][1]['ports']['dq'] = [['dq', 6, 8]]
        with self.assertRaises(AssertionError):
            _mini(km, self.VIEWS, self.FROM)

    def test_output_driven_twice_refused(self):
        km = json.loads(json.dumps(self.KM))
        km['dsfd_hstnv_10']['copies'][1]['ports']['dq'] = [['dq', 5, 9]]
        with self.assertRaises(AssertionError):
            _mini(km, self.VIEWS, self.FROM)

    def test_slice_wider_than_standard_refused(self):
        km = json.loads(json.dumps(self.KM))
        km['dsfd_hstnv_10']['copies'][0]['ports'] = dict(di=[['di', 0, 6]], dq=[['dq', 0, 6]])
        with self.assertRaises(AssertionError):
            _mini(km, self.VIEWS, self.FROM)

    def test_unbound_target_refused(self):
        km = json.loads(json.dumps(self.KM))
        km['dsfd_hstnv_10']['copies'][1]['to'] = 'dsfd_hstnv_5'
        with self.assertRaises(SystemExit):
            _mini(km, self.VIEWS, self.FROM)


class KcopyGenerated(unittest.TestCase):
    """the real map on the generator's own write_netlist, bound by tools/die_port_bind.py against the closed RTL"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        r = subprocess.run([sys.executable, str(ROOT / 'tools/s81/prove_dedupe_pad.py'), '--kcopy', '--map', str(MAP),
                            '--out', str(cls.out / 'pos')], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        cls.src = (cls.out / 'pos/die.v').read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def bind(self, src=None):
        d = self.out / 'pos'
        (d / 'die_b.v').write_text(self.src if src is None else src)
        (d / 'die_b.v.pads.json').write_text((d / 'die.v.pads.json').read_text())
        files = [x for x in (d / 'run.sh').read_text().split() if x.endswith('.sv') and x != 'tb.sv']
        cmd = [sys.executable, str(ROOT / 'tools/die_port_bind.py'), str(d / 'die_b.v'), '--top', 'kcopy_die',
               '--rtl-root', str(d / 'empty'), '--out', str(d / 'report.json')]
        for f in files:
            cmd += ['--rtl-file', str(d / f)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p, json.loads((d / 'report.json').read_text())

    def test_bind_pass_with_declared_pads(self):
        p, d = self.bind()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(d['verdict'], 'PASS')
        rec = json.loads((self.out / 'pos/model.json').read_text())
        self.assertEqual(rec['kcopy']['by_master'], {k: 1 for k in json.loads(MAP.read_text())['kcopy']})
        self.assertEqual(rec['kcopy']['copies'], 16)
        pads = json.loads((self.out / 'pos/die.v.pads.json').read_text())['instances']
        self.assertEqual(pads['hx_E__k1']['ports']['i']['logical_width'], 537)
        self.assertEqual(pads['u4__k1']['ports']['di']['logical_width'], 2047)

    def test_l2r_second_copy_lane_order(self):
        # copy B: i = {28 PAD, i[1100:565], i[0]}; od[537:0] = ob; st no-load
        line = next(l for l in self.src.splitlines() if ' hx_E__k1 (' in l)
        self.assertRegex(line, r"\.i\(\{28'b0, n_q\d+_i__kc565, n_q\d+_i\}\)")
        self.assertRegex(line, r"\.od\(\{n_pad_hx_E__k1_od, n_q\d+_ob\}\)")
        self.assertIn('.st(n_kcnc_hx_E__k1_st)', line)

    def test_spare_pad_tied_one_rejected(self):
        src = self.src.replace("{28'b0, ", "{28'hfffffff, ", 1)
        self.assertNotEqual(src, self.src)
        p, d = self.bind(src)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('input_tied', d['failing'])


if __name__ == '__main__':
    unittest.main()
