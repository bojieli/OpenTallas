"""KIT-OPS-5 11-15: an "(advisory)" line is never the item's error reason."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def test_advisory_line_is_filtered_like_admission_chatter():
    ln = "TAP-RADIUS-TARGET ot_s81sl_leaf__t21: grid+explicit tap clk_t28 radius=230.416/200 (advisory)"
    assert KW.ADMISSION.search(ln)


def test_real_error_line_is_kept():
    assert not KW.ADMISSION.search("Error: global_route.tcl, 194 GRT-0232")
    assert not KW.ADMISSION.search("[ERROR DRT-0255] Maze Route cannot find path")
