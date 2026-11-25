"""kvpc_exact_m45: M4/M5 OBS become exact, M1-M3 stay blanket, pins and M6/M7 unchanged."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kvpc_exact_m45 as K

HEAD = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 100 BY 50 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  1 49.5 1.05 50 ;
    END
  END a
  PIN VSS
    DIRECTION INOUT ;
    USE GROUND ;
    PORT
      LAYER M5 ;
        RECT  10 1 10.12 49 ;
    END
  END VSS
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT  12 1 12.12 49 ;
    END
  END VDD
"""
BASE = HEAD + "".join(f"  OBS\n" if i == 0 else "" for i in range(1)) + "".join(
    f"    LAYER M{i} ;\n     RECT  0 0 100 50 ;\n" for i in range(1, 6)) + \
    "    LAYER M6 ;\n     RECT  30 30 31 31 ;\n  END\nEND core\n"
DETAIL = HEAD + "  OBS\n    LAYER M4 ;\n     RECT  20 20 30 20.1 ;\n    LAYER M5 ;\n     RECT  40 0 40.1 50 ;\n" \
    "    LAYER M6 ;\n     RECT  0 0 100 50 ;\n  END\nEND core\n"


def _run(tmp_path, detail_obs, *extra):
    (tmp_path / "b.lef").write_text(BASE)
    (tmp_path / "d.lef").write_text(HEAD + detail_obs + "END core\n")
    out = tmp_path / "n.lef"
    rc = K.main(["--base", str(tmp_path / "b.lef"), "--detail", str(tmp_path / "d.lef"), "--out", str(out),
                 "--receipt", str(tmp_path / "r.json"), *extra])
    return rc, out.read_text()


def _rects(text, layer):
    seg = text.split("  OBS\n")[1]
    seg = seg.split(f"LAYER {layer} ;")[1].split("LAYER")[0]
    return [tuple(map(float, l.split()[1:5])) for l in seg.splitlines() if l.strip().startswith("RECT")]


def test_v1_exact_with_zero_grow(tmp_path):
    rc, new = _run(tmp_path, "  OBS\n    LAYER M4 ;\n     RECT  20 20 30 20.1 ;\n    LAYER M5 ;\n     RECT  40 0 40.1 50 ;\n", "--grow-um", "0")
    assert rc == 0
    assert new.split("  OBS\n")[0] == HEAD
    for i in (1, 2, 3):
        assert f"LAYER M{i} ;\n     RECT  0 0 100 50 ;" in new
    assert _rects(new, "M4") == [(20.0, 20.0, 30.0, 20.1)] and _rects(new, "M5") == [(40.0, 0.0, 40.1, 50.0)]
    assert "RECT  30 30 31 31 ;" in new


def test_v2_grow_merge_and_pin_clear(tmp_path):
    # two M4 wires 0.09 apart (< 2 x pitch) merge into one grown shape; a third 0.2 away stays separate
    obs = ("  OBS\n    LAYER M4 ;\n     RECT  20 20 30 20.024 ;\n     RECT  20 20.114 30 20.138 ;\n"
           "     RECT  20 20.338 30 20.362 ;\n    LAYER M5 ;\n     RECT  40 0 40.024 50 ;\n")
    rc, new = _run(tmp_path, obs)
    assert rc == 0
    m4 = _rects(new, "M4")
    assert (19.952, 19.952, 30.048, 20.186) in m4 and len(m4) == 2
    assert min(r[0] for r in m4) == 19.952
    m5 = _rects(new, "M5")
    assert m5 == [(39.952, 0.0, 40.072, 50.0)]
    st = json.loads((tmp_path / "r.json").read_text())["grow_merge"]
    assert st["grow_um"] == 0.048 and st["stats"]["M4"]["rects_after"] == 2 and st["stats"]["M4"]["rects_before"] == 3
    assert new.split("  OBS\n")[0] == HEAD
    assert "RECT  30 30 31 31 ;" in new


def test_v3_pin_shape_cut_foreign_spacing_kept(tmp_path):
    # pin a (M4) is (1, 49.5)-(1.05, 50).  Its own wire (0.5 .. 1.05) must leave the pin shape ...
    own = "  OBS\n    LAYER M4 ;\n     RECT  0.5 49.5 1.05 50 ;\n    LAYER M5 ;\n     RECT  40 0 40.024 50 ;\n"
    rc, new = _run(tmp_path, own)
    assert rc == 0
    assert not any(r[0] < 1.05 and r[2] > 1.0 and r[1] < 50 and r[3] > 49.5 for r in _rects(new, "M4"))
    # ... while a FOREIGN wire 0.05 beside the pin keeps its whole grown shape (v2 cut it back to 1.098)
    foreign = "  OBS\n    LAYER M4 ;\n     RECT  1.1 49.5 5 50 ;\n    LAYER M5 ;\n     RECT  40 0 40.024 50 ;\n"
    rc, new = _run(tmp_path, foreign)
    assert rc == 0
    m4 = _rects(new, "M4")
    assert min(r[0] for r in m4) == 1.052 and max(r[2] for r in m4) == 5.048


def test_v3_no_sliver_below_min_width(tmp_path):
    # a foreign wire 0.003 wide beside the pin cut would leave slivers; every M4/M5 OBS rect is >= 0.024 in both directions
    obs = ("  OBS\n    LAYER M4 ;\n     RECT  0.5 49.5 1.05 50 ;\n     RECT  1.1 49.5 5 50 ;\n     RECT  7 10 7.003 20 ;\n"
           "    LAYER M5 ;\n     RECT  40 0 40.024 50 ;\n")
    rc, new = _run(tmp_path, obs)
    assert rc == 0
    for L in ("M4", "M5"):
        for r in _rects(new, L):
            assert min(round(r[2] - r[0], 3), round(r[3] - r[1], 3)) >= 0.024, (L, r)
    st = json.loads((tmp_path / "r.json").read_text())["grow_merge"]["stats"]
    assert st["M4"]["dropped"] == 0


def test_fix_slivers_regrow_and_drop():
    bbox = (0, 0, 10000, 10000)
    clear = [(0, 0, 100, 1000)]
    res = [(100, 0, 3000, 1000), (100, 2000, 103, 3000), (50, 1000, 100, 1010), (9990, 5000, 10000, 5010)]
    out, st = K.fix_slivers(res, clear, 24, bbox)
    assert st["slivers_found"] == 3 and st["regrown"] == 3 and st["dropped"] == 0
    assert all(min(r[2] - r[0], r[3] - r[1]) >= 24 for r in out)
    assert not any(r[0] < 100 and r[2] > 0 and r[1] < 1000 and r[3] > 0 for r in out)      # never over the pin shape
    assert all(0 <= r[0] and r[2] <= 10000 for r in out)
    # nothing can grow without touching the pin: dropped
    out2, st2 = K.fix_slivers([(100, 0, 110, 1000)], [(0, 0, 105, 1000), (105, 0, 400, 1000)], 24, bbox)
    assert st2["dropped"] == 1 and out2 == []


def test_v3_real_metal_stays_covered_and_inside(tmp_path):
    obs = "  OBS\n    LAYER M4 ;\n     RECT  0 10 0.024 10.024 ;\n     RECT  50 49.99 80 50 ;\n    LAYER M5 ;\n     RECT  40 0 40.024 50 ;\n"
    rc, new = _run(tmp_path, obs)
    assert rc == 0
    for L in ("M4", "M5"):
        for r in _rects(new, L):
            assert r[0] >= 0 and r[1] >= 0 and r[2] <= 100 and r[3] <= 50      # inside the macro outline
    m4 = _rects(new, "M4")
    assert any(r[0] <= 0 and r[2] >= 0.024 and r[1] <= 10 and r[3] >= 10.024 for r in m4)   # edge wire still covered


def test_splice_args_fixed():
    a = K.splice_args("b", "d", "o")
    assert a[a.index("--layers") + 1] == "M4,M5" and a[a.index("--bloat-factor") + 1] == "0"


def test_union_minus():
    r = K.union_minus([(0, 0, 10, 10), (5, 0, 20, 10)], [(8, 0, 12, 10)])
    assert sorted(r) == [(0, 0, 8, 10), (12, 0, 20, 10)]
