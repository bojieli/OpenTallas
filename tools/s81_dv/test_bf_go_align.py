"""S81-BF-GOBF (11-11): every BF front of the bound frame masters sees go_bf (xb_meta[0], on the x2 payload) and its
sequencer's go_e / cfg / f_prog through the same register depth.

Fast gate (no simulation): the checked-in rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv / col_h10_l4.sv are parsed, every
BF front's x payload (x0 / x1 / xb_data / xb_meta) and control (cfifo cc -> cfg7_seq_bfp lc, + go / cfg / f_prog) are
traced with tools/s81_dv/station_depth.py (station depth read from the bound RTL), and any skew FAILS.  With 2-flop
stations (dc23a738f3) the c26l taps leave col_h9 e13 / col_h10 e15 x2 one edge late (the BF16 fault of S81-FRAME-FIX-1);
the generator's nobfalign form must show exactly that skew (negative control).  OT_S81_FRAME_L4_RTL=<dir> checks
another copy of the frame_l4 RTL (e.g. the pre-fix main files).

LP / kit / band-plan forms (rtl/dsrom_sys/s81_dv/frame_lp/**/col_<M>_l4_lp*.sv: the landed parent, its rf3r twin, the
vg / vgc / vgy kits and twins, the vgch / vgcs band forms and the plan / plan_kit / plan_kit_cr band contents the die
binds): the depth is proven on frame_l4 above (and measured on the vgcs twin, frame_bf_measure.sh); here every form must
carry the alignment stage unchanged: the last BF front's go / cfg / f_prog are exactly the outputs of its
u_y_ga_<e>_<pin>_0 relays, fed by the same nets as in frame_l4 and clocked by the front's own clock (no landing / seam
between them).  The legacy rf3 / rf3r kits (kit/*_kit_rf3*.sv, frame_kit.py main, not in the die chain) are not checked.
OT_S81_FRAME_LP_RTL=<dir> checks another copy of the frame_lp tree."""
import collections
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / 'tools')]
import frame_wrap as FW  # noqa: E402

L4 = Path(os.environ.get('OT_S81_FRAME_L4_RTL') or ROOT / 'rtl/dsrom_sys/s81_dv/frame_l4')
LP = Path(os.environ.get('OT_S81_FRAME_LP_RTL') or ROOT / 'rtl/dsrom_sys/s81_dv/frame_lp')
LAST = {'col_h9': 'u_e13', 'col_h10': 'u_e15'}
ANY_INST = re.compile(r'^\s*(?:/\*.*?\*/\s*)?(?:reg .*?;\s*)*?(\w+)\s+(?:#\((?:[^()]|\([^()]*\))*\)\s*)?(u_\w+) \((\..*)\);(?:\s*//.*)?$')
CRS4 = 'rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv'
INST = re.compile(r'^    (\w+)(?: #\(.*?\))? (u_\w+) \((\..*)\);(?:\s*//.*)?$')
CONN = re.compile(r'\.(\w+)\((\{[^{}]*\}|[^(){}]*)\)')
Q = 'ot_v41_rom_elem_q_qxpq_w10'


def index():
    idx = FW.rtl_index()
    t = FW.DPB.preprocess(FW.DPB.strip_comments((ROOT / CRS4).read_text()), {})
    for mod in FW.DPB.parse_modules(t, CRS4):
        idx.setdefault(mod.name, mod)
    return idx


def parse_frame(path):
    insts = []
    for ln in path.read_text().split('\n'):
        m = INST.match(ln)
        if not m:
            continue
        cs = collections.OrderedDict()
        for c in CONN.finditer(m.group(3)):
            v = c.group(2).strip()
            cs[c.group(1)] = [b.strip() for b in v[1:-1].split(',')] if v.startswith('{') else [v]
        insts.append(dict(master=m.group(1), name=m.group(2), conns=cs))
    return insts


class BfGoAlign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx = index()

    def skews(self, m):
        insts = parse_frame(L4 / f'{m}_l4.sv')
        bf = FW.elem_skew(insts, self.idx)
        q = FW.elem_skew(insts, self.idx, (Q,), FW.Q_X_PINS, FW.Q_CTL_PINS)
        return bf, q

    def test_bound_frames_aligned(self):
        for m, nbf in (('col_h9', 3), ('col_h10', 4)):
            bf, q = self.skews(m)
            self.assertEqual(len(bf), nbf, m)
            self.assertEqual(len(q), 12, m)
            bad = {k: v for k, v in bf.items() if v['x'] != v['ctl']}
            self.assertEqual(bad, {}, f'{m}: BF front x2 / control depth skew (go_bf sampled off its go_e edge)')
            self.assertEqual({k: v for k, v in q.items() if v['x'] != v['ctl']}, {}, f'{m}: q element skew')

    def lp_files(self, m):
        fs = [f for f in sorted(LP.rglob(f'{m}_l4_lp*.sv')) if not re.search(r'_kit_rf3r?\.sv$', f.name)]
        return [f for f in fs if re.search(rf'\bdsfd_bf_front_roots\b.*\b{LAST[m]} \(', f.read_text())]

    def test_lp_forms_carry_alignment(self):
        for m, e in LAST.items():
            ref = {i['name']: i for i in parse_frame(L4 / f'{m}_l4.sv')}
            files = self.lp_files(m)
            self.assertGreaterEqual(len(files), 12, (m, [f.name for f in files]))
            for f in files:
                with self.subTest(m=m, file=str(f.relative_to(LP))):
                    insts = {}
                    for ln in f.read_text().split('\n'):
                        mm = ANY_INST.match(ln)
                        if mm and mm.group(2) in [e] + [f'u_y_ga_{e[2:]}_{p}_0' for p in FW.BF_CTL_PINS]:
                            cs = {c.group(1): c.group(2).strip() for c in CONN.finditer(mm.group(3))}
                            insts.setdefault(mm.group(2), []).append(cs)
                    self.assertIn(e, insts)
                    for fr in insts[e]:
                        for p in FW.BF_CTL_PINS:
                            ga = f'u_y_ga_{e[2:]}_{p}_0'
                            self.assertIn(ga, insts, f'{f.name}: {e}.{p} without its alignment relay {ga}')
                            rl = next(r for r in insts[ga] if r['o'] == fr[p])  # the relay that drives this front
                            rr = ref[ga]['conns']
                            self.assertEqual(rl['i'].replace(' ', ''), '{' * (len(rr['i']) > 1) + ','.join(rr['i']) +
                                             '}' * (len(rr['i']) > 1), f'{f.name}: {ga} input differs from frame_l4')
                            self.assertEqual(rl['ck'], fr['ck'], f'{f.name}: {ga} not on {e}.ck')

    def test_generator_negative_control(self):
        """the c26l taps without the alignment stage: x2 exactly one edge late at the last BF front only"""
        import dsrom_s81_fulldie as F
        pq = F._receipt_params(F.BOUND_VIEW_RECEIPTS[Q])
        for m, last in (('col_h9', 'u_e13'), ('col_h10', 'u_e15')):
            for al in (False, True):
                insts, names, _, _, rec = FW.build(m, self.idx, pq, True, bf_align=al)
                sk = {names[k]: v['x'] - v['ctl'] for k, v in FW.elem_skew(insts, self.idx).items()}
                want = {k: (1 if (k == last and not al) else 0) for k in sk}
                self.assertEqual(sk, want, (m, al))
            ch = next(c for c in rec['changes'] if c['kind'] == 'bf_go_align')
            self.assertEqual({k: v['added'] for k, v in ch['fronts'].items() if v['added']}, {last[2:]: 1}, m)


if __name__ == '__main__':
    unittest.main()
