"""CORE-OBS-COV (COORD 11-12): checker capacity model -- a hard core blocks a layer only where its LEF OBS covers
> 50% of the core area on that layer; otherwise the layer is free minus the OBS share.  Declared obs_max and LEF-less
cores block as before; die_core_rects (used by physical outputs) is unchanged."""
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check  # noqa: E402
import die_trial as D  # noqa: E402

DETAIL = """MACRO cdet
  SIZE 100 BY 100 ;
  PIN clk
    PORT
      LAYER M7 ;
        RECT 0 0 1 1 ;
    END
  END clk
  OBS
    LAYER M5 ;
      RECT 0 0 100 100 ;
    LAYER M6 ;
      RECT 0 0 10 10 ;
      RECT 5 5 15 15 ;
    LAYER M7 ;
      RECT 0 0 100 2 ;
  END
END cdet
"""
BLANKET = DETAIL.replace("RECT 0 0 100 2 ;", "RECT 0 0 100 100 ;").replace("cdet", "cblk")


def _plan(d, cores):
    t = {"outline_um": [300, 100], "hard_cores": cores}
    return types.SimpleNamespace(parts={"p0": {"type": "t", "origin_um": [1000, 2000]}}, types={"t": t},
                                 layer_budget={"partition_signal_max": "M7"})


def _lefs(d):
    a, b = os.path.join(d, "det.lef"), os.path.join(d, "blk.lef")
    open(a, "w").write(DETAIL)
    open(b, "w").write(BLANKET)
    return a, b


def test_lef_layer_cover_union_area():
    with tempfile.TemporaryDirectory() as d:
        a, b = _lefs(d)
        c = D.lef_layer_cover(a)
        assert abs(c["M5"] - 1.0) < 1e-9
        assert abs(c["M6"] - (100 + 100 - 25) / 1e4) < 1e-9      # overlapping rects counted once
        assert abs(c["M7"] - 0.02) < 1e-9                         # the M7 pin is not an obstruction
        assert D.lef_layer_cover(b)["M7"] == 1.0
        assert D.lef_layer_cover(os.path.join(d, "missing.lef")) is None


def test_detail_view_frees_m6_m7_blanket_blocks():
    with tempfile.TemporaryDirectory() as d:
        a, b = _lefs(d)
        P = _plan(d, [{"inst": "u0", "origin_um": [0, 0], "outline_um": [100, 100], "lef": a},
                      {"inst": "u1", "origin_um": [200, 0], "outline_um": [100, 100], "lef": b}])
        blk5, part5 = D.die_core_cover(P, "M5")
        assert len(blk5) == 2 and not part5
        blk7, part7 = D.die_core_cover(P, "M7")
        assert blk7 == [(1200, 2000, 1300, 2100)]                  # blanket M7 blocks
        assert part7 == [(1000, 2000, 1100, 2100, 0.02)]          # detail M7 is free minus 2 %
        # physical/abstract model unchanged: both cores still solid to M7 there
        assert len(D.die_core_rects(P, "M7")) == 2


def test_missing_lef_and_obs_max_keep_old_model():
    with tempfile.TemporaryDirectory() as d:
        a, _ = _lefs(d)
        P = _plan(d, [{"inst": "u0", "origin_um": [0, 0], "outline_um": [100, 100], "lef": a, "obs_max": "M7"},
                      {"inst": "u1", "origin_um": [200, 0], "outline_um": [100, 100], "lef": os.path.join(d, "no.lef"),
                       "obs_max": "M6"}])
        blk7, part7 = D.die_core_cover(P, "M7")
        assert blk7 == [(1000, 2000, 1100, 2100)] and not part7   # declared obs_max M7 still blocks
        blk6, part6 = D.die_core_cover(P, "M6")
        assert len(blk6) == 2 and not part6                       # LEF-less core (obs_max M6) solid as before


def test_cut_interval_tracks_derate():
    base = check.cut_interval_tracks(0, 100, 0.1, 0.25)
    assert abs(base - 250) < 1e-6
    assert check.cut_interval_tracks(0, 100, 0.1, 0.25, (), (), ()) == base
    got = check.cut_interval_tracks(0, 100, 0.1, 0.25, derate=[(0, 50, 0.04)])
    assert abs(got - (125 * 0.96 + 125)) < 1e-6
    assert abs(check.cut_interval_tracks(0, 100, 0.1, 0.25, blocked=[(0, 50)], derate=[(0, 50, 0.04)]) - 125) < 1e-6
