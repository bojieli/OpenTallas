import unittest

import leaf_transport as T
import lower_vpx as V


def route(sl, sid, k, dn, up, pdsk):
    return dict(slice=sl, sid=sid, leaf=k, xr_command_to_leaf_boundary_edges=dn, vn_b_partial_to_xr_input_edges=up, pdsk_edges=pdsk)


def report(dn2=4):
    rows = []
    for sl in range(16):
        for k in range(5):
            rows.append(route(f'u_s_{sl // 2}{"SN"[sl % 2]}', sl, k, 4 + (k if sl else (k if k < 3 else dn2 - 2)), 4, k))
    return dict(schema='opentallas.s81.emitted_leaf_boundary_routes.v1', verdict='PASS_SELECTED_BOUNDARY_WIRING', leaves=rows)


class Test(unittest.TestCase):
    def test_asbuilt_lo(self):
        s = dict(sid=0, dn=[4] * 5, up=[4] * 5, pdsk=[0] * 5)
        self.assertEqual(T.lo_after_ctl(s, 2), V.LO_AFTER_CTL)

    def test_eng_merges_equal_round_trips(self):
        s = dict(sid=0, dn=[2, 2, 5, 5, 9], up=[2] * 5, pdsk=[0] * 5)
        self.assertEqual(T.eng_ctls(s), [(0, 16), (4, 12), (7, 3)])

    def test_norm_clash_is_reported(self):
        s = dict(sid=0, dn=[2, 3, 5, 5, 9], up=[2] * 5, pdsk=[0] * 5)
        self.assertEqual(T.norm_issue(s)[1], [[2, 3]])

    def test_period_default_unchanged_and_landed_margin(self):
        self.assertEqual(V.beat_period(), 6)
        self.assertEqual(V.beat_period(), V.beat_period(V.LO_AFTER_CTL))     # S81-XTIER-FIX: as-built = its own value
        self.assertGreaterEqual(V.beat_period(17), 6)
        self.assertNotEqual(V.beat_period(18) and 18 % V.beat_period(18), 0)

    def test_incomplete_cohort_rejected(self):
        r = report()
        r['leaves'].pop()
        with self.assertRaises(ValueError):
            T.slices(r)


if __name__ == '__main__':
    unittest.main()
