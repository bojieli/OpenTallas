"""C-RST-TAP-REPOINT: reset_taps.tcl keeps the original reset net when a FIRM-flop re-point would exceed OT_RESET_REPOINT_MAX_UM (default off).
Source-contract test with mutants (the flow itself is proved by the hd_st_n3_turn CTS-only replay)."""
import re
from pathlib import Path
import pytest

SRC = (Path(__file__).parent / "reset_taps.tcl").read_text()


def _ok(s):
    m = re.search(r"if \{\$k == \$best\} \{ incr rt_keep; continue \}(.*?)\$it disconnect", s, re.S)
    assert m, "re-point block not found"
    blk = m.group(1)
    assert "OT_RESET_REPOINT_MAX_UM" in blk
    assert "info exists ::env(OT_RESET_REPOINT_MAX_UM)" in blk              # default off: unset = no change
    assert "$bd > $::env(OT_RESET_REPOINT_MAX_UM) * $rt_dbu" in blk     # Manhattan leg vs limit, in dbu
    assert re.search(r"incr rt_far;.*?\n\s*continue", blk, re.S)           # refused: continue before disconnect = original net kept
    assert "OT_RESET_REPOINT_KEPT" in s


def test_contract():
    _ok(SRC)


@pytest.mark.parametrize("old,new", [
    ("[info exists ::env(OT_RESET_REPOINT_MAX_UM)] && ", ""),
    ("$bd > $::env(OT_RESET_REPOINT_MAX_UM)", "$bd < $::env(OT_RESET_REPOINT_MAX_UM)"),
    ("        continue\n      }\n      $it disconnect", "      }\n      $it disconnect"),
])
def test_mutant_killed(old, new):
    assert old in SRC
    with pytest.raises(AssertionError):
        _ok(SRC.replace(old, new, 1))
