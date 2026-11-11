"""grt_split_view: GRT view drops only the named OBS layers; share/region adjustment follow the detailed OBS."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grt_split_view as G

LEF = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 10.24 BY 6.4 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  0 1 0.05 1.02 ;
    END
  END a
  OBS
      LAYER M5 ;
        RECT  0 0 10.24 6.4 ;
      LAYER M6 ;
        RECT  0 0 5.12 6.4 ;
      LAYER M7 ;
        RECT  0 0 10.24 0.064 ;
  END
END core
END LIBRARY
"""


def test_grt_view_drops_only_named_layers():
    g = G.grt_view(LEF, {"M6", "M7"})
    assert "LAYER M5" in g and "LAYER M6" not in g and "LAYER M7" not in g
    assert "PIN a" in g and "SIZE 10.24 BY 6.4" in g
    assert G.check(LEF, g, {"M6", "M7"})
    assert not G.check(LEF, LEF, {"M6", "M7"})


def test_grt_view_keeps_everything_else_byte_identical():
    g = G.grt_view(LEF, {"M6", "M7"})
    a = [l for l in LEF.split("\n") if "M6" not in l and "M7" not in l and "RECT  0 0 5.12" not in l and "RECT  0 0 10.24 0.064" not in l]
    assert g.split("\n") == a


def test_share_matches_geometry():
    s = G.share(LEF, ["M6", "M7"], {})
    assert abs(s["M6"]["blocked_share"] - 0.5) < 0.02      # left half of every horizontal M6 track
    assert s["M7"]["blocked_share"] < 0.02                 # one 64-nm band across vertical M7 tracks
    assert s["M6"]["rects"] == 1 and s["M7"]["rects"] == 1


def test_region_tcl_prices_share_plus_margin():
    t = G.region_tcl("core", {"M6": 0.55, "M7": 0.06})
    assert 'getName] ne "core"' in t
    assert "set_global_routing_region_adjustment $::gsv_r -layer M6 -adjustment 0.550" in t
    assert "-layer M7 -adjustment 0.060" in t


def test_main_region_tcl_is_disabled(tmp_path):
    f = tmp_path / "c.lef"; f.write_text(LEF)
    out = tmp_path / "r.tcl"
    assert G.main(["region-tcl", "--lef", str(f), "--master", "core", "--margin", "0.05", "--out", str(out)]) == 2
    assert not out.exists()


def test_bands_only_remove_capacity_and_keep_rest(tmp_path):
    f = tmp_path / "c.lef"; f.write_text(LEF)
    out = tmp_path / "g.lef"
    assert G.main(["grt-view", "--bands", "--lef", str(f), "--out", str(out), "--gcell", "0.57", "--margin", "0.05"]) == 0
    g = out.read_text()
    # everything but M6/M7 OBS is byte-identical to the detailed view
    assert G.grt_view(g, {"M6", "M7"}) == G.grt_view(LEF, {"M6", "M7"})
    sh = G.share(g, ["M6", "M7"], {})
    # M7 removed (default band layer is M6 only); M6 priced at calib*(0.5+0.05) by thin H bands, never above detail+margin
    assert sh["M7"]["blocked_share"] == 0
    m6 = [l.split() for l in g.splitlines() if l.strip().startswith("RECT") and l.split()[3] == "10.240"]
    assert m6, "M6 bands span the full width"
    period = 0.57 / round(0.8 * 0.55, 3)
    assert len(m6) == int((6.4 - period / 2 + 0.016) // period) + 1
    assert all(abs(float(r[4]) - float(r[2]) - 0.032) < 1e-9 for r in m6)


def test_channels_stay_open_on_their_layers(tmp_path):
    f = tmp_path / "c.lef"; f.write_text(LEF)
    ch = tmp_path / "ch.json"
    ch.write_text('[{"dir": "EW", "span_um": [2.0, 3.0], "layers": ["M5", "M6"], "reason": "t"}]')
    out = tmp_path / "g.lef"
    assert G.main(["grt-view", "--bands", "--lef", str(f), "--out", str(out), "--channels", str(ch)]) == 0
    head, groups, tail = G.split_obs(out.read_text())
    for lay, lines in groups:
        for l in lines[1:]:
            x0, y0, x1, y1 = (float(v) for v in l.split()[1:5])
            if lay in ("M5", "M6"):
                assert y1 <= 2.0 + 1e-9 or y0 >= 3.0 - 1e-9, (lay, l)
    # M5 blanket OBS is split around the channel, not dropped
    m5 = [l for lay, ls in groups if lay == "M5" for l in ls[1:]]
    assert len(m5) == 2
    # M7 (not a channel layer) is untouched by the channel (removed by the default band mode anyway)
    assert all(lay != "M7" for lay, _ in groups)
