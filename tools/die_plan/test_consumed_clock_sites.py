import unittest
import schema as S
import gen_phys as G


class TinyPlan:
    layer_budget = {'partition_signal_max': 'M7'}
    layers = {'M7': {'dir': 'V', 'pitch_um': .08, 'offset_um': .04},
              'M6': {'dir': 'H', 'pitch_um': .064, 'offset_um': .032}}

    def __init__(self, macro_x):
        self.types = {'t': {'module': 'fixture', 'outline_um': [40., 40.],
                           'hard_cores': [{'inst': 'body', 'origin_um': [macro_x, 0.],
                                           'outline_um': [16., 40.]}]}}


class ConsumedClockSites(unittest.TestCase):
    def site(self, p, x=8.64, y=20., taken=()):
        return S.tap_clear(p.types['t'], x, y, taken, strict=True,
                           pin_snap=lambda a,b: G._snap_tap(p,a,b),
                           legal_axes=G.clock_legal_axes(p,'t'))

    def test_raw_zero_width_shore_does_not_imply_a_clock_track(self):
        p = TinyPlan(17.28)
        self.assertEqual(S.tap_clear(p.types['t'],8.64,20.,strict=True),(8.64,20.))
        with self.assertRaisesRegex(ValueError,'no legal clock tap'):
            self.site(p)

    def test_real_shore_finds_consumed_pg_safe_pin(self):
        p = TinyPlan(18.72)
        q = self.site(p)
        self.assertEqual(G._snap_tap(p,*q),q)
        self.assertGreaterEqual(q[0],8.64)
        self.assertLessEqual(q[0],18.72-8.64+1e-8)

    def test_legal_axes_use_both_pg_phases_and_actual_tracks(self):
        p = TinyPlan(18.72)
        xs,ys = G.clock_legal_axes(p,'t')
        for axis,ln in [(xs,'M7'),(ys,'M6')]:
            for q in axis:
                self.assertFalse(any(S.pg_blocked(ln,q-origin) for origin in (0.,G.CORE_MARGIN_UM)))
        for x,y in zip(xs[::11],ys[::11]):
            self.assertEqual(G._snap_tap(p,x,y),(x,y))

    def test_l1_site_matches_exhaustive_consumed_lattice(self):
        p=TinyPlan(18.72);xs,ys=G.clock_legal_axes(p,'t');target=(20.,20.);taken=[(9.16,20.)]
        q=self.site(p,*target,taken)
        def free(x,y):
            return (x<=18.72-8.64+1e-8 and
                    not any(abs(x-a)<8.64-1e-8 and abs(y-b)<8.64-1e-8 for a,b in taken))
        legal=[(x,y) for x in xs for y in ys if free(x,y)]
        self.assertTrue(legal)
        expected=min(abs(x-target[0])+abs(y-target[1]) for x,y in legal)
        self.assertAlmostEqual(abs(q[0]-target[0])+abs(q[1]-target[1]),expected,7)

    def test_existing_nonclock_anchor_call_unchanged(self):
        p=TinyPlan(18.72)
        self.assertEqual(S.tap_clear(p.types['t'],8.64,20.,strict=True),(8.64,20.))


if __name__=='__main__':
    unittest.main()
