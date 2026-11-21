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


def test_info_not_blocking_line_is_filtered():
    """BUILD-SETTINGS-AUDIT-1900: TAP-LIMIT-INFO / COLLECTOR-REACH-INFO label themselves info; never the decisive line"""
    for ln in ("TAP-LIMIT-INFO ot_s81sl_leaf__t2: grid+explicit tap clk_t28 load=898/1000, radius=226.024/200.0, empty=False "
               "(info: not blocking; routed timing decides)",
               "TAP-LIMIT-INFO t: explicit tap clk_t1 load=3/1000, radius=1/200, empty=False (info, LIMIT-BIND-1: not blocking)",
               "COLLECTOR-REACH-INFO u_c reach 310/300 (info: not blocking)"):
        assert KW.ADMISSION.search(ln), ln
    log = "gen phys: start\nError: gen_phys.py killed by signal 15\nTAP-LIMIT-INFO t: grid tap x load=1/2 (info: not blocking; routed timing decides)\n"
    assert KW.decisive_line(log).startswith("Error: gen_phys.py killed")
    log2 = "step a\nstep b done\nTAP-LIMIT-INFO t: grid tap x load=1/2 (info: not blocking; routed timing decides)\n"
    assert KW.decisive_line(log2) == "step b done"


def test_info_word_inside_an_error_is_kept():
    assert not KW.ADMISSION.search("ERROR TAP-0001 tap info missing: blocking")
    assert not KW.ADMISSION.search("Error: info not blocking (x) and more")
