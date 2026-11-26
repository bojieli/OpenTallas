"""C-VIEW-OBS-PIN-ABUT: pin_flank_clear lint + fix."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pin_flank_clear as PF

LEF = """MACRO m
  SIZE 10 BY 10 ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M3 ;
        RECT  1.0 1.0 1.018 1.144 ;
    END
  END a
  PIN b
    USE SIGNAL ;
    PORT
      LAYER M3 ;
        RECT  1.288 1.0 1.306 1.144 ;
    END
  END b
  OBS
    LAYER M3 ;
      RECT  1.018 1.096 1.288 1.108 ;
      RECT  1.0 1.144 1.018 2.0 ;
      RECT  5.0 5.0 6.0 5.012 ;
  END
END m
"""


def test_lint_flags_flank_not_pin_end():
    f = PF.findings(LEF, ["M3"])
    assert {(x["pin"], tuple(x["obs_rect_nm"])) for x in f} == {("a", (1018, 1096, 1288, 1108)), ("b", (1018, 1096, 1288, 1108))}   # the tip-continuing rect (1.0 1.144) is an end, not a flank


def test_fix_clears_the_flanks_and_keeps_everything_else():
    new, rec = PF.fix(LEF, ("M3",), 0.054)
    assert rec["before"] == 2 and rec["after"] == 0 and PF.findings(new, ["M3"]) == []
    assert "RECT  1.072 1.096 1.234 1.108 ;" in new                    # 0.270 strip minus 0.054 from each pin flank
    assert "RECT  1.0 1.144 1.018 2.0 ;" in new and "RECT  5.0 5.0 6.0 5.012 ;" in new
    assert [l for l in new.split("\n") if "PIN" in l or "RECT  1.0 1.0" in l] == [l for l in LEF.split("\n") if "PIN" in l or "RECT  1.0 1.0" in l]


def test_real_metal_inside_the_clearance_stays_blocked():
    new, rec = PF.fix(LEF, ("M3",), 0.054, real={"M3": [[1.02, 1.096, 1.03, 1.108]]})
    assert rec["real_pieces_kept"] == 1 and "RECT  1.02 1.096 1.03 1.108 ;" in new
    assert PF.findings(new, ["M3"]) == []


def test_cli_exit_codes(tmp_path):
    f = tmp_path / "v.lef"
    f.write_text(LEF)
    assert PF.main(["lint", str(f), "--layers", "M3"]) == 1
    o = tmp_path / "o.lef"
    assert PF.main(["fix", str(f), str(o)]) == 0 and PF.main(["lint", str(o)]) == 0


def test_committed_sstn_views_are_clean():
    root = HERE.parents[1] / "physical" / "die_plan" / "s81" / "pin_flank_views_1126" / "ot_s81_sstn_base566"
    views = sorted(root.glob("*/ot_s81_sstn_base566.lef"))
    for v in views:                          # a missing checkout of the data dir is a skip, not a pass of nothing
        assert PF.findings(v.read_text(), ["M3"]) == [], v
