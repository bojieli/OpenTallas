"""abstract_detail: only OBS above the PG pin layer is replaced; everything else stays byte-identical."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_detail as A

BASE = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 100 BY 50 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
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
  OBS
    LAYER M1 ;
     RECT  0 0 100 50 ;
    LAYER M5 ;
     RECT  0 0 100 50 ;
    LAYER M6 ;
     RECT  0 0 100 50 ;
    LAYER M7 ;
     RECT  0 0 100 50 ;
  END
END core
"""

DETAIL_OBS = """  OBS
    LAYER M1 ;
     RECT  0 0 3 3 ;
    LAYER M6 ;
     RECT  20 20 30 20.1 ;
     RECT  40 5 60 5.1 ;
    LAYER M7 ;
     RECT  50 0 50.2 50 ;
  END
END core
"""


def _detail(tmp_path, base=BASE):
    head = base.split("  OBS\n")[0]
    p = tmp_path / "detail.lef"
    p.write_text(head + DETAIL_OBS)
    return p


def test_default_layers_are_above_pg_pin_layer():
    assert A.default_layers(BASE.splitlines(True)) == ["M6", "M7"]


def test_splice_keeps_pins_and_lower_obs(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(BASE)
    out = tmp_path / "new.lef"
    rc = A.main(["splice", "--base", str(b), "--detail", str(_detail(tmp_path)), "--out", str(out)])
    assert rc == 0
    new = out.read_text()
    assert new.split("  OBS\n")[0] == BASE.split("  OBS\n")[0]
    assert "LAYER M1 ;\n     RECT  0 0 100 50 ;" in new  # lower layer stays blanket
    assert "RECT  20 20 30 20.1 ;" in new and "RECT  50 0 50.2 50 ;" in new
    m6 = new.split("LAYER M6 ;")[1].split("LAYER M7")[0]
    assert "0 0 100 50" not in m6
    assert A.main(["check", "--base", str(b), "--new", str(out)]) == 0


def test_check_rejects_pin_change(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(BASE)
    bad = tmp_path / "bad.lef"
    bad.write_text(BASE.replace("RECT  10 1 10.12 49", "RECT  10 1 10.12 48"))
    assert A.main(["check", "--base", str(b), "--new", str(bad)]) == 1


def test_splice_flags_detail_from_other_odb(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(BASE)
    other = _detail(tmp_path, BASE.replace("SIZE 100 BY 50", "SIZE 100 BY 51"))
    assert A.main(["splice", "--base", str(b), "--detail", str(other), "--out", str(tmp_path / "n.lef")]) == 1


def test_clear_pins_cuts_own_metal_and_near_wire_only():
    base = """  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 1 0.084 1.024 ;
    END
  END a
  PIN VSS
    USE GROUND ;
    PORT
      LAYER M4 ;
        RECT 5 5 6 6 ;
    END
  END VSS
""".splitlines(keepends=True)
    det = {"M4": ["        RECT 0.06 1 0.2 1.024 ;\n",   # own stub: only the part under the pin leaves
                  "        RECT 0.1 1.05 0.3 1.07 ;\n",  # neighbour 26 nm away, x from 0.1: inside the 0.048 grow
                  "        RECT 5.5 5.5 5.6 5.6 ;\n",    # under a PG pin: untouched
                  "        RECT 3 3 4 4 ;\n"],
           "M5": ["        RECT 0 1 0.084 1.024 ;\n"]}
    new, rep = A.clear_pins(det, base, 0.048, ["M4"])
    r4 = [tuple(float(v) for v in l.split()[1:5]) for l in new["M4"]]
    assert (5.5, 5.5, 5.6, 5.6) in r4 and (3, 3, 4, 4) in r4
    assert (0.132, 1, 0.2, 1.024) in r4                     # stub keeps what is beyond the grown box
    assert (0.132, 1.05, 0.3, 1.07) in r4
    assert rep["M4"]["rects_cut"] == 2 and rep["M4"]["overlap_own_pin"] == 1
    assert new["M5"] == det["M5"]                           # no pin on M5: untouched
