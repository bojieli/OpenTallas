"""KW-FIX-44 11-10 (COORD rulings (3)): the two grt183_make.sh stage stops reach the autopilot classes COORD named:
OT_GRT_CONGESTED_FAIL -> STRUCTURAL grt-overflow -> wave ROUTING; OT_GRT_TIMECAP -> STRUCTURAL grt-timecap -> wave TIMING.
    python3 -m pytest -q tools/autopilot/test_grt_stop_classify.py"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402
import kit_wave as KW  # noqa: E402

CONG = ("OT_GRT_CONGESTED_FAIL stage=grt full global route ended with congestion: total overflow 83032 >= 1000; "
        "stopping before repair/incremental reroute (KW-FIX-44 GRT-INCR-CONGESTED) 2026-11-10 22:00:00")
CAP = ("OT_GRT_TIMECAP stage=grt post-route repair over 21660 s (cap 21600 s) hold_ws_ps=-12.50 setup_wns=unmeasured "
       "last='repair_design -verbose' (KW-FIX-44) 2026-11-10 22:00:00")


def probe_patterns():
    """the classify probe's pattern table, as the remote probe compiles it"""
    src = AP.PROBE_CLASSIFY
    i = src.index("pat = {")
    j = src.index("}", src.index('"orfs_error"', i)) + 1
    return eval(src[i + len("pat = "):j], {})


def test_probe_patterns_catch_both_lines():
    pat = probe_patterns()
    assert re.search(pat["congestion"], "x\n" + CONG + "\n").group(0) == CONG
    assert re.search(pat["grt_timecap"], "x\n" + CAP + "\n").group(0) == CAP
    assert not re.search(pat["grt_timecap"], CONG) and not re.search(pat["congestion"], CAP)
    assert re.search(pat["congestion"], "[ERROR GRT-0116] Global routing finished with congestion.")   # unchanged


def test_classify_kinds():
    assert AP.classify({"congestion": CONG}, {"exit": 21}) == ("STRUCTURAL", "grt-overflow", CONG)
    assert AP.classify({"grt_timecap": CAP}, {"exit": 21}) == ("STRUCTURAL", "grt-timecap", CAP)


def test_wave_classes():
    for kind, why, cls in (("grt-overflow", CONG, "ROUTING"), ("grt-timecap", CAP, "TIMING")):
        j = {"status": "DONE-STRUCTURAL", "kind": kind, "reasons": why, "signoff": None}
        stage, st, c, msg = KW.queue_class(j)
        assert (st, c) == ("FAIL", cls), (kind, stage, st, c, msg)
        assert why[:40] in msg
