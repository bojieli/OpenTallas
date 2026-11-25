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
    assert m5 == [(39.952, -0.048, 40.072, 50.048)]
    st = json.loads((tmp_path / "r.json").read_text())["grow_merge"]
    assert st["grow_um"] == 0.048 and st["stats"]["M4"]["rects_after"] == 2 and st["stats"]["M4"]["rects_before"] == 3
    assert new.split("  OBS\n")[0] == HEAD
    assert "RECT  30 30 31 31 ;" in new


def test_v2_pin_zone_stays_open(tmp_path):
    # signal pin a is on M4 at (1, 49.5)-(1.05, 50): the grown wire next to it is cut back by the pin clearance
    obs = "  OBS\n    LAYER M4 ;\n     RECT  1.1 49.5 5 50 ;\n    LAYER M5 ;\n     RECT  40 0 40.024 50 ;\n"
    rc, new = _run(tmp_path, obs)
    assert rc == 0
    assert all(r[0] >= 1.098 - 1e-9 for r in _rects(new, "M4"))


def test_splice_args_fixed():
    a = K.splice_args("b", "d", "o")
    assert a[a.index("--layers") + 1] == "M4,M5" and a[a.index("--bloat-factor") + 1] == "0"


def test_union_minus():
    r = K.union_minus([(0, 0, 10, 10), (5, 0, 20, 10)], [(8, 0, 12, 10)])
    assert sorted(r) == [(0, 0, 8, 10), (12, 0, 20, 10)]
