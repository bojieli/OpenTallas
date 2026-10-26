"""QC-MP-REGION unit tests: plan-computed leg balance is exact at TT and drawn detours have the planned length."""
import math
import region_clock as RC


def test_fit_leg_exact_tt_and_seg_limit():
    for L in (100.0, 436.0, 1287.36, 3568.32):
        nat = RC.stage_delay(L, RC.n_min(L))
        for pad in (0.0, 13.0, 52.7, 400.0, 964.0):
            n, det = RC.fit_leg(L, nat + pad, ff_target=None)
            assert det >= 0 and n >= RC.n_min(L)
            assert (L + det) / n <= RC.REP_UM + 1e-6
            d = RC.stage_delay(L + det, n)
            # exact unless no (n, detour) exists (segment cap forces one more stage): then never short and the
            # overshoot (< one stage) is absorbed by the parent node's re-fit (settle loop)
            assert d >= nat + pad - 1e-6 and d - (nat + pad) < RC.STAGE["TT"][0] + 1e-6


def test_polyline_detour_length():
    a, b = (0.0, 0.0), (1000.0, 300.0)
    for xf in (True, False):
        for at_end in (False, True):
            poly = RC.polyline(a, b, xf, 240.0, at_end)
            Lp = sum(RC.md(poly[i], poly[i + 1]) for i in range(len(poly) - 1))
            assert math.isclose(Lp, 1300.0 + 240.0, abs_tol=1e-6)
            assert tuple(poly[0]) == a and tuple(poly[-1]) == b


def test_place_reps_additive_and_legal():
    class AllLegal:
        def bay(self, xy):
            return True
    poly = RC.polyline((0.0, 0.0), (2000.0, 0.0), True, 0.0)
    pts, ok, L, cs = RC.place_reps(poly, 6, AllLegal())
    assert ok and len(pts) == 5 and math.isclose(L, 2000.0)
    b = [0.0] + cs + [L]
    assert max(b[i + 1] - b[i] for i in range(len(b) - 1)) <= RC.REP_UM + 1e-6
