"""DIE-QC-47: --clock-type-keepouts makes a type's clock.keepouts_um a forbidden die clock-cell site (+2.16 um halo).
Default off keeps SiteMap byte-identical (KV plan_c already carries tile keep-outs that the die tree never read)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import die_trial as D  # noqa: E402


class _P:
    W, H = 400.0, 200.0
    die = {}
    types = {"phy": {"outline_um": [200.0, 200.0], "clock": {"keepouts_um": [[0.0, 0.0, 150.0, 190.0]]}},
             "soft": {"outline_um": [200.0, 200.0]}}
    parts = {"p0": {"type": "phy", "origin_um": [0.0, 0.0], "orient": "R0"},
             "p1": {"type": "phy", "origin_um": [200.0, 0.0], "orient": "MX"},
             "s": {"type": "soft", "origin_um": [0.0, 200.0], "orient": "R0"}}

    def to_die(self, n, q):
        p = self.parts[n]
        x, y = q
        if p["orient"] == "MX":
            y = self.types[p["type"]]["outline_um"][1] - y
        return p["origin_um"][0] + x, p["origin_um"][1] + y


def _site(flag):
    old = D.CLOCK_TYPE_KEEPOUTS
    try:
        D.CLOCK_TYPE_KEEPOUTS = flag
        return D.SiteMap(_P())
    finally:
        D.CLOCK_TYPE_KEEPOUTS = old


def test_default_off_ignores_type_keepouts():
    s = _site(False)
    assert s.forb == []
    assert s.legal((75.0, 95.0))


def test_opt_in_forbids_keepout_plus_halo_in_die_frame():
    s = _site(True)
    assert len(s.forb) == 2 and {r[4] for r in s.forb} == {"keepout"}
    assert s.why((75.0, 95.0)) == "keepout"           # inside the R0 body
    assert s.why((151.0, 95.0)) == "keepout"          # inside the 2.16 um halo
    assert s.legal((153.0, 95.0))                     # outside body + halo
    assert s.legal((75.0, 193.0))                     # free strip above the R0 body
    # MX instance: type y [0,190] -> die y [10,200]; the free strip is now at the bottom
    assert s.why((275.0, 100.0)) == "keepout"
    assert s.legal((275.0, 5.0))
    assert s.why((275.0, 8.5)) == "keepout"           # halo below the mirrored body


def test_ot_clk_argv_maps_top_type_keepouts():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clk"))
    import inspect
    import ot_clk
    src = inspect.getsource(ot_clk)
    assert 'top.get("type_keepouts")' in src and '"--clock-type-keepouts"' in src
