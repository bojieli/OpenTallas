"""--rly-face-pins / --col-reset-tree / relay_face_audit (S-DIE-RELAYFACE 2026-10-16, VIS-ROM S81F-01/08, D-S81-02)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsrom_s81_fulldie as S  # noqa: E402
import relay_face_audit as RFA  # noqa: E402


def _m(insts, buses):
    return dict(insts=insts, buses=buses, regions=[dict(name='frame_0', kind='field', rect=(0.0, 0.0, 4000.0, 4000.0))])


def _I(name, master, x, y, w=20.0, h=20.0, kind='blk'):
    return S.Inst(name, master, x, y, w, h, kind=kind, region='frame_0')


class FacesFromPins(unittest.TestCase):
    def run_pass(self, insts, buses, closed=()):
        bv = {f'dsfd_rly_{b}_{fi}{fo}': dict(text='', w=17.0, h=17.0) for b, fi, fo in closed}
        S._RFP_BV.clear()
        with patch.object(S, 'bound_views', return_value=bv), patch.object(S, '_lint_pin_pt', return_value=lambda *a: None), \
                patch.object(S, '_assigned_record', return_value=None):
            m = _m(insts, buses)
            S._relay_faces_by_pins(m)
        return m

    def test_driver_west_takes_west_input(self):
        # S81F-01: driver W of the relay, load E: the old centre rule gave in-face W too, but --x-site-pair forced E->W;
        # the pin pass picks W -> E
        d, r, l_ = _I('d', 'blk', 0, 100), _I('r', 'dsfd_rly_283_EW', 200, 100, 34.56, 30.24, 'rly'), _I('l', 'blk', 500, 100)
        m = self.run_pass([d, r, l_], [('a', 'x_lane', 283, [('d', 'o'), ('r', 'i')]),
                                       ('b', 'x_lane', 283, [('r', 'o'), ('l', 'i')])])
        self.assertEqual(r.master, 'dsfd_rly_283_WE')
        self.assertEqual(m['rly_face_pins']['changed'], 1)

    def test_same_side_is_not_forced_to_the_opposite_face(self):
        # S81F-08: driver and load both W: never the far E face; without closed masters an L master, U recorded as a kit
        d, r, l_ = _I('d', 'blk', 0, 100), _I('r', 'dsfd_rly_63_WE', 300, 100, 17.0, 17.0, 'rly'), _I('l', 'blk', 0, 98.5)
        m = self.run_pass([d, r, l_], [('a', 'x_lane', 63, [('d', 'o'), ('r', 'i')]),
                                       ('b', 'x_lane', 63, [('r', 'o'), ('l', 'i')])])
        fi, fo = S.RLY_FACES[r.master]
        self.assertIn('W', (fi, fo))                  # one pin on the peers' face, the other an L (never E)
        self.assertNotIn('E', (fi, fo))
        self.assertIn('dsfd_rly_63_WW', m['rly_face_pins']['kit_requests'])

    def test_only_closed_masters_when_the_width_has_any(self):
        d, r, l_ = _I('d', 'blk', 0, 100), _I('r', 'dsfd_rly_63_EW', 300, 100, 17.0, 17.0, 'rly'), _I('l', 'blk', 600, 300)
        self.run_pass([d, r, l_], [('a', 'x_lane', 63, [('d', 'o'), ('r', 'i')]),
                                   ('b', 'x_lane', 63, [('r', 'o'), ('l', 'i')])],
                      closed=[(63, 'W', 'E'), (63, 'N', 'S')])
        self.assertEqual(r.master, 'dsfd_rly_63_WE')

    def test_chain_settles(self):
        # relay -> relay chain going N: both relays S -> N
        d = _I('d', 'blk', 100, 0)
        r1, r2 = _I('r1', 'dsfd_rly_15_EW', 100, 300, 17, 17, 'rly'), _I('r2', 'dsfd_rly_15_EW', 100, 600, 17, 17, 'rly')
        l_ = _I('l', 'blk', 100, 900)
        self.run_pass([d, r1, r2, l_], [('a', 'cfg', 15, [('d', 'o'), ('r1', 'i')]),
                                        ('b', 'cfg', 15, [('r1', 'o'), ('r2', 'i')]),
                                        ('c', 'cfg', 15, [('r2', 'o'), ('l', 'i')])])
        self.assertEqual((r1.master, r2.master), ('dsfd_rly_15_SN', 'dsfd_rly_15_SN'))


class ResetTree(unittest.TestCase):
    def test_equal_depth_and_fanout(self):
        insts = [_I('cf0', 'blk', 1000, 0, 40, 40)] + [_I(f's{i}', 'blk', 100 + 60 * (i % 30), 100 + 120 * (i // 30), 20, 20)
                                                       for i in range(450)]
        buses = [('rs_col_0', 'col_reset', 1, [('cf0', 'rs')] + [(f's{i}', 'rs') for i in range(450)]),
                 ('ck_col_0', 'col_clock', 1, [('cf0', 'co')] + [(f's{i}', 'ck') for i in range(450)])]
        m = _m(insts, buses)
        P = S.Placer(m)
        old = S.COL_RESET_TREE
        try:
            S.COL_RESET_TREE = 32
            S._col_reset_tree(m, P)
        finally:
            S.COL_RESET_TREE = old
        rs = [b for b in m['buses'] if b[1] == 'col_reset']
        self.assertTrue(all(len(b[3]) - 1 <= 32 for b in rs))
        # every original sink is driven by exactly one stage, at the same number of stages from cf0.rs
        drv = {e: b[3][0] for b in rs for e in b[3][1:]}
        def stages(e):
            n = 0
            while drv[e] != ('cf0', 'rs'):
                e = (drv[e][0], 'i')
                n += 1
            return n
        depths = {stages((f's{i}', 'rs')) for i in range(450)}
        self.assertEqual(len(depths), 1)
        self.assertEqual(depths.pop(), m['col_reset_tree']['columns']['rs_col_0']['depth'])
        ck = [b for b in m['buses'] if b[0] == 'ck_col_0'][0][3]
        self.assertTrue(all((it.name, 'ck') in ck for it in m['insts'] if it.name.startswith('z_rs')))


class StationPitch2(unittest.TestCase):
    def test_one_lane_station_two_tracks_centred(self):
        for horiz in (True, False):
            mst = 'dsfd_stnh_86x1' if horiz else 'dsfd_stnv_86x1'
            w, h = (17.28, 17.28)
            it = S.Inst('f0', mst, 0, 0, w, h, kind='stn')
            Mx = S.Q.Master(mst, w, h, 3, 't')
            ports = dict(fi0=('input', 1), di0=('input', 86), fo0=('output', 1), do0=('output', 86))
            m = dict(insts=[it], buses=[])
            old = S.STN_PIN_PITCH2
            try:
                S.STN_PIN_PITCH2 = True
                S._faces_r8(m, Mx, it, ports)
            finally:
                S.STN_PIN_PITCH2 = old
            r = S.Q.pin_rects(Mx, 1, {p_: b for p_, (_d, b) in ports.items()})
            along = lambda q: ((q[1] + q[3]) / 2 if horiz else (q[0] + q[2]) / 2)
            for a, b in (('fi0', 'di0'), ('fo0', 'do0')):
                cs = sorted(along(q) for n_, _l, q in r if n_.split('[')[0] in (a, b))
                self.assertEqual(len(cs), 87)
                self.assertTrue(all(abs((y - x) - 0.096) < 1e-6 for x, y in zip(cs, cs[1:])))
                self.assertAlmostEqual((cs[0] + cs[-1]) / 2, 8.652, places=6)    # M4/M5 track nearest 8.64
            rec = m['stn_pin_pitch2'][mst]
            self.assertAlmostEqual(rec['clock_pin'], 4.524)
            self.assertAlmostEqual(rec['data_last'], 12.78)
            self.assertEqual(cs[0], rec['clock_pin'])


class Audit(unittest.TestCase):
    LEF = """MACRO R
  SIZE 10 BY 10 ;
  PIN i[0]
    PORT
      LAYER M4 ;
        RECT 9.9 5 10 5.1 ;
    END
  END i[0]
  PIN o[0]
    PORT
      LAYER M4 ;
        RECT 0 5 0.1 5.1 ;
    END
  END o[0]
END R
MACRO B
  SIZE 10 BY 10 ;
  PIN o[0]
    PORT
      LAYER M4 ;
        RECT 9.9 5 10 5.1 ;
    END
  END o[0]
  PIN i[0]
    PORT
      LAYER M4 ;
        RECT 0 5 0.1 5.1 ;
    END
  END i[0]
END B
"""

    def test_input_behind_the_face(self):
        class I:
            def __init__(s, n, m, x, y, o='R0'):
                s.name, s.master, s.x, s.y, s.orient = n, m, x, y, o
        # relay R: in on E, out on W; driver B west of it -> input faces away (wraps), load east -> output faces away
        ins = [I('d', 'B', 0, 0), I('dsfd_r', 'dsfd_rly_1_EW', 100, 0), I('l', 'B', 300, 0)]
        lef = self.LEF.replace('MACRO R', 'MACRO dsfd_rly_1_EW').replace('END R\n', 'END dsfd_rly_1_EW\n')
        rec = RFA.audit(ins, [('a', 'x', 1, [('d', 'o'), ('dsfd_r', 'i')]), ('b', 'x', 1, [('dsfd_r', 'o'), ('l', 'i')])],
                        [lef], top=0)
        t = rec['totals']['dsfd_rly_']
        self.assertEqual((t['in_away'], t['in_wrap'], t['out_away'], t['out_wrap']), (1, 1, 1, 1))
        # mirrored (MY) the faces look at their peers
        ins[1].orient = 'MY'
        rec = RFA.audit(ins, [('a', 'x', 1, [('d', 'o'), ('dsfd_r', 'i')]), ('b', 'x', 1, [('dsfd_r', 'o'), ('l', 'i')])],
                        [lef], top=0)
        t = rec['totals']['dsfd_rly_']
        self.assertEqual((t.get('in_away', 0), t.get('out_away', 0)), (0, 0))


if __name__ == '__main__':
    unittest.main()
