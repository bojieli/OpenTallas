"""kvpc_exact_m45: M4/M5 OBS become exact, M1-M3 stay blanket, pins and M6/M7 unchanged."""
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


def test_m4_m5_exact_rest_unchanged(tmp_path):
    (tmp_path / "b.lef").write_text(BASE)
    (tmp_path / "d.lef").write_text(DETAIL)
    out = tmp_path / "n.lef"
    assert K.main(["--base", str(tmp_path / "b.lef"), "--detail", str(tmp_path / "d.lef"), "--out", str(out)]) == 0
    new = out.read_text()
    assert new.split("  OBS\n")[0] == HEAD
    for i in (1, 2, 3):
        assert f"LAYER M{i} ;\n     RECT  0 0 100 50 ;" in new
    m4 = new.split("LAYER M4 ;")[2].split("LAYER M5")[0]
    assert "0 0 100 50" not in m4 and "RECT  20 20 30 20.1 ;" in new
    assert "RECT  40 0 40.1 50 ;" in new
    assert "RECT  30 30 31 31 ;" in new and "RECT  0 0 100 50 ;\n  END" not in new.split("LAYER M6 ;")[1][:5]


def test_splice_args_fixed():
    a = K.splice_args("b", "d", "o")
    assert a[a.index("--layers") + 1] == "M4,M5" and a[a.index("--bloat-factor") + 1] == "0"
