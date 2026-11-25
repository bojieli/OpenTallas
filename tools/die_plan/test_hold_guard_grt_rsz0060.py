"""QC-HOLD-STRUCT 11-25: RSZ-0060 in a GRT hold chunk is the guard's own buffer cap; the log says so and the catch stays."""
from pathlib import Path

T = (Path(__file__).resolve().parent / "hold_guard_grt.tcl").read_text()


def test_chunk_cap_is_announced_before_the_call():
    i = T.index("an RSZ-0060 line below is this cap, not a failure")
    j = T.index("::ot_hg_rth_orig {*}$base -hold -max_buffer_percent $pct")
    assert i < j


def test_rsz0060_is_caught_per_chunk_not_fatal():
    assert "regexp {RSZ-0060|Max buffer count} $err" in T
    assert "set capped 1; set hit 1" in T
    assert "RSZ-0060 caught per chunk" in T
