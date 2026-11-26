"""view_lint.py (VIEW-NOOBS, C-VIEW-NO-OBS).   python3 -m pytest -q tools/die_plan/test_view_lint.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import view_lint as V  # noqa: E402

PIN = "  PIN {n}\n    DIRECTION INOUT ;\n    USE {u} ;\n    PORT\n      LAYER {l} ;\n        RECT 0 0 1 1 ;\n    END\n  END {n}\n"
HEAD = "MACRO m\n  SIZE 10 BY 10 ;\n"
OBS = "  OBS\n    LAYER M1 ;\n      RECT 0 0 10 10 ;\n  END\nEND m\n"


def test_signal_pins_only_no_obs_is_flagged_like_norm_finish():
    t = HEAD + PIN.format(n="a", u="SIGNAL", l="M5") + "END m\n"
    assert V.lef_problems(t) == ["no OBS", "no PG pins"]


def test_obs_without_pg_and_pg_without_obs():
    assert V.lef_problems(HEAD + PIN.format(n="a", u="SIGNAL", l="M5") + OBS) == ["no PG pins"]
    assert V.lef_problems(HEAD + PIN.format(n="VDD", u="POWER", l="M4") + "END m\n") == ["no OBS"]


def test_good_view_is_clean():
    assert V.lef_problems(HEAD + PIN.format(n="VDD", u="POWER", l="M4") + PIN.format(n="VSS", u="GROUND", l="M4") + OBS) == []


def test_plan_findings(tmp_path):
    bad = tmp_path / "bad.lef"
    bad.write_text(HEAD + PIN.format(n="a", u="SIGNAL", l="M5") + "END m\n")
    good = tmp_path / "good.lef"
    good.write_text(HEAD + PIN.format(n="VDD", u="POWER", l="M4") + OBS)
    raw = {"partition_types": {"t1": {"hard_cores": [{"module": "ot_s81dv_norm_finish", "lef": "bad.lef"}]},
                               "t2": {"hard_cores": [{"module": "ok", "lef": "good.lef"}, {"module": "ghost", "lef": "missing.lef"}]},
                               "t3": {"hard_cores": [{"module": "ot_s81dv_norm_finish", "lef": "bad.lef"}]}}}
    out = V.findings(raw, str(tmp_path / "plan.json"))
    assert len(out) == 1 and out[0].startswith("FAIL VIEW-NOOBS ot_s81dv_norm_finish:") and "no OBS and no PG pins" in out[0]
    assert "t1, t3" in out[0]
