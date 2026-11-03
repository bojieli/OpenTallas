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
