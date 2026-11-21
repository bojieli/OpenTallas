"""TT setup repair keep-or-restore on the RELOADED DB (hd_serdes sd2: in-session -43.92, reloaded -127.85, before -55.88)."""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tt_setup_keep as K  # noqa: E402


def test_sd2_case_restores_before_db(tmp_path):
    rep = tmp_path / "rep.log"; mea = tmp_path / "mea.log"
    rep.write_text("OT_TT_SETUP_REPAIR before TT setup wns -55.88 tns -4554.00\nOT_TT_SETUP_REPAIR after TT setup wns -43.92 tns -388.00\n")
    mea.write_text("OT_TT_SETUP_REPAIR measure TT setup wns -127.85 tns -1524.00\n")
    r = subprocess.run([sys.executable, "-I", str(HERE / "tt_setup_keep.py"), str(rep), str(mea)], capture_output=True, text=True)
    assert r.returncode == 1 and "RESTORE before" in r.stdout and "worse" in r.stdout    # the in-session -43.92 is ignored


def test_improved_reloaded_db_is_kept(tmp_path):
    rep = tmp_path / "rep.log"; mea = tmp_path / "mea.log"
    rep.write_text("OT_TT_SETUP_REPAIR before TT setup wns -77.72 tns -6877.27\n")
    mea.write_text("OT_TT_SETUP_REPAIR measure TT setup wns -31.60 tns -52.60\n")
    assert subprocess.run([sys.executable, "-I", str(HERE / "tt_setup_keep.py"), str(rep), str(mea)], capture_output=True).returncode == 0


@pytest.mark.parametrize("before,after,keep", [
    ((-10.0, -50.0), (-5.0, -50.0), True),      # wns better, tns equal
    ((-10.0, -50.0), (-10.0, -20.0), True),     # tns better, wns equal
    ((-10.0, -50.0), (-5.0, -80.0), False),     # wns better but tns worse
    ((-10.0, -50.0), (-12.0, -10.0), False),    # tns better but wns worse
    ((-10.0, -50.0), (-10.0, -50.0), False),    # no change: keep the original
    ((-10.0, -50.0), None, False),              # no reload number: restore
    (None, (-1.0, 0.0), False),
])
def test_decide(before, after, keep):
    assert K.decide(before, after)[0] is keep


def test_tcl_measure_mode_and_no_buffer_removal_at_grt():
    t = (HERE / "tt_setup_repair.tcl").read_text()
    assert "OT_TT_SETUP_MEASURE" in t and "ot_tt_wns measure" in t
    repair_dispatch = "ot_bounded_repair tt_setup_repair [list ::ot_tt_chunk"
    assert t.index("ot_tt_wns measure") < t.index(repair_dispatch)
    chunk = t.split("proc ::ot_tt_chunk", 1)[1].split("proc ::ot_tt_measure", 1)[0]
    assert "repair_timing -setup -setup_margin" in chunk
    line = [l for l in t.splitlines() if "lappend extra -skip_buffer_removal" in l][0]
    assert 'ot_tt_rc eq "grt"' in line


def test_run_kit_steps_gate_the_swap_on_the_keep_decision():
    g = (HERE / "gen_phys.py").read_text()
    assert '"tt_setup_keep.py"' in g
    repair_swaps = [line for line in g.splitlines() if "/work/tt_setup_keep.py" in line]
    assert len(repair_swaps) == 2
    for line in repair_swaps:
        assert line.index("OT_TT_SETUP_MEASURE=1") < line.index("/work/tt_setup_keep.py") < line.index("then mv -f")
