"""The shared PV_LEAD requires actual equal-depth start branches."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / 'tools')]
import kv_bundle_eq as BEQ
import kv_k_rt_eq as EQ
from test_kv_bundle_eq import _model, _stub_K


class PvStartEquality(unittest.TestCase):
    def test_long_branch_uses_legal_successive_hops(self):
        K, F = _stub_K()
        source, sink, cap = (1000.0, 1000.0), (2600.0, 1000.0), 400.0
        obstacle = F.Inst('obstacle', 'hard', 1700.0, 900.0, 200.0, 200.0, 'R0')
        m = dict(insts=[obstacle], die=dict(w=6000.0, h=6000.0))
        pads = BEQ._place_pads(K, m, [], source, sink, 6, 52.68, 30.24, cap)
        previous = source
        for p in pads:
            a, b = (p.x, p.y + (p.h + K.SHAVE) / 2), (p.x + p.w + K.SHAVE, p.y + (p.h + K.SHAVE) / 2)
            self.assertLessEqual(abs(a[0] - previous[0]) + abs(a[1] - previous[1]), cap + 1e-6)
            self.assertTrue(BEQ._free(m, [obstacle], p.x, p.y, p.w + K.SHAVE, p.h + K.SHAVE))
            previous = b
        self.assertLessEqual(abs(previous[0] - sink[0]) + abs(previous[1] - sink[1]), cap + 1e-6)

    def test_fork_is_physically_padded_and_recorded(self):
        K, F = _stub_K()
        # This inherited bundle fixture has a long direct fork; allow space
        # for its single added station while testing the fork age accounting.
        K.width_reach = lambda bits: 1200.0
        K.PIN_REACH = K.HOP_REACH = 1200.0
        m = _model(F)
        names = {'d2d_kv': 'kvs_attn', 'kvs_attn': 'pvw_0', 'kvs_ctl': 'pvw_1'}
        for it in m['insts']:
            it.name = names.get(it.name, it.name)
        m['buses'] = [(bid, cl, bits, [(names.get(i, i), 'pvst' if i == 'd2d_kv' and p == 'srx'
                                     else 'st' if p == 'd2d__srx' else p) for i, p in eps])
                      for bid, cl, bits, eps in m['buses']]
        pin = K.pin_xy
        K.pin_xy = lambda it, mm, port: pin(it, mm, {'pvst': 'srx', 'st': 'd2d__srx'}.get(port, port))
        m['relay_stages']['ks_pvst'] = 1
        m['forks'] = {'ks_pvst': [('pvw_1', 'st')]}
        m['fork_stages'] = {'ks_pvst__f0': 0}
        n = len(m['insts'])
        EQ.equalize_pv_start(K, m)
        actual = BEQ._walk(m, {i.name: i for i in m['insts']}, ('kvs_attn', 'pvst'))
        self.assertEqual([actual[(f'pvw_{p}', 'st')][0] for p in (0, 1)], [1, 1])
        self.assertEqual(len(m['insts']), n + 1)
        self.assertEqual(m['relay_stages']['ks_pvst'], 1)
        self.assertEqual(m['fork_stages']['ks_pvst__f0'], 1)
        self.assertEqual(m['pv_start_eq']['ages'], [1, 1])


if __name__ == '__main__':
    unittest.main()
