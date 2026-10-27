"""CLOCK-KV-R11 opt-in helpers: core frame (origin + track_offset, orient) and canonical island snap."""
import die_clock_mesh as DCM


class _P:
    parts = {"p": {"type": "t"}}

    def __init__(self, core):
        self._core = core

    def to_type(self, part, pt):
        return (pt[0] - 1000.0, pt[1] - 2000.0)

    def to_die(self, part, pt):
        return (pt[0] + 1000.0, pt[1] + 2000.0)

    def ptype(self, part):
        return {"hard_cores": [self._core]}


def _core(orient):
    return {"inst": "c0", "module": "m", "outline_um": [250.0, 400.0], "origin_um": [86.4, 17.28],
            "track_offset_um": [0.016, 0.0], "orient": orient}


def test_core_frame_round_trip_all_orients():
    for o in ("R0", "MX", "MY", "R180"):
        c = _core(o); P = _P(c)
        q = (1000 + 86.416 + 30.0, 2000 + 17.28 + 50.0)
        u, v = DCM.core_frame(P, "p", c, q)
        back = DCM.core_frame(P, "p", c, (u, v), inverse=True)
        assert abs(back[0] - q[0]) < 1e-9 and abs(back[1] - q[1]) < 1e-9
        assert abs(u - (220.0 if o in ("MY", "R180") else 30.0)) < 1e-9


def test_canon_snap_within_tol_and_reject_outside():
    for o in ("R0", "MY"):
        c = _core(o); P = _P(c)
        site = DCM.core_frame(P, "p", c, (125.0, 86.4), inverse=True)
        q = (site[0] + 0.016, site[1])
        pt, d = DCM.canon_island_point(P, "p/c0", q, {"m": [[125.0, 86.4]]}, 0.05)
        assert abs(pt[0] - site[0]) < 1e-9 and abs(d - 0.016) < 1e-9
        _, d2 = DCM.canon_island_point(P, "p/c0", (site[0] + 1.0, site[1]), {"m": [[125.0, 86.4]]}, 0.05)
        assert d2 is None
    assert DCM.canon_island_point(_P(_core("R0")), "p/c0", (1.0, 2.0), {}, 0.05) == ((1.0, 2.0), 0.0)
