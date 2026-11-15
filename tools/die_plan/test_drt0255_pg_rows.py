"""DRT0255 (FABLE-PD-DRT-1350 fixes 1 and 3): GRT per-gcell capacity cut on PG pair rows / columns (pg_track_truth.tcl region mode) and
ring / station site search that skips the std rows under the M6 pair (face_flops.tcl ff_pair_rows_build).  Tcl logic is run with tclsh;
OpenROAD-bound parts are checked by text."""
import copy
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402

TCLSH = shutil.which("tclsh")


def _tcl(script):
    r = subprocess.run([TCLSH], input=script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def _proc(src, name):
    """the text of proc `name` (signature + body) from a tcl file: brace-matched past the argument list"""
    t = (HERE / src).read_text()
    i = t.index(f"proc {name} ")
    k = t.index("{", i)                       # argument list
    depth = 0
    for j in range(k, len(t)):
        depth += t[j] == "{"
        depth -= t[j] == "}"
        if depth == 0:
            break
    k2 = t.index("{", j)                      # body
    depth = 0
    for j in range(k2, len(t)):
        depth += t[j] == "{"
        depth -= t[j] == "}"
        if depth == 0:
            break
    return t[i:j + 1]


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_pair_rows_build_blocks_the_rows_under_the_pair_and_its_spacing():
    # M6 pair 0.288 / 0.096 / 0.288 at y 1968..2640 dbu (1 um = 1000 dbu), spacing 32, row height 270
    out = _tcl(_proc("face_flops.tcl", "ff_pair_rows_build") + "\nputs [lsort -integer [dict keys [ff_pair_rows_build 0 270 {{1968 2640}} 32]]]")
    rows = [int(x) for x in out.split()]
    # pair + spacing spans 1936..2672 -> rows 7 (1890-2160), 8 (2160-2430), 9 (2430-2700)
    assert rows == [7, 8, 9]
    # one row of 270 dbu per 4.32 um pitch repeat: the next pair is 4320 dbu higher -> rows 7+16 ...
    out2 = _tcl(_proc("face_flops.tcl", "ff_pair_rows_build") + "\nputs [lsort -integer [dict keys [ff_pair_rows_build 0 270 {{1968 2640} {6288 6960}} 32]]]")
    assert [int(x) for x in out2.split()] == [7, 8, 9, 23, 24, 25]


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_illegal_span_is_wire_edge_within_spacing_of_the_stripe():
    out = _tcl(_proc("pg_track_truth.tcl", "ot_pgtt_illegal_span") + "\nputs [ot_pgtt_illegal_span 1968 2640 16 32]")
    assert out == "1920 2688"


def test_region_mode_is_default_off_and_emits_the_adjustment_not_obstructions():
    t = (HERE / "pg_track_truth.tcl").read_text()
    assert 'OT_PG_TRACK_TRUTH_MODE) eq "region"' in t
    assert "set_global_routing_region_adjustment $um -layer $ln -adjustment 1.0" in t
    # the obstruction branch is untouched: still created when the mode is not region
    assert t.count("odb::dbObstruction_create") == 2 and t.index("if {[ot_pgtt_region_mode]}") < t.index("odb::dbObstruction_create")
    assert "OT_PG_TRACK_TRUTH removed" in t       # remove proc unchanged


def test_ff_put_near_skips_pair_rows_only_with_the_flag():
    t = (HERE / "face_flops.tcl").read_text()
    assert t.count("[ff_pair_row_blocked $r]") == 2
    body = _proc("face_flops.tcl", "ff_pair_row_blocked")
    assert 'OT_PG_PAIR_ROW_KEEPOUT) ne "1"} { return 0 }' in body            # flag off = never blocked


def test_config_lines_only_with_the_gen_env(monkeypatch):
    for k in ("OT_PG_TRACK_TRUTH_MODE", "OT_PG_PAIR_ROW_KEEPOUT"):
        monkeypatch.delenv(k, raising=False)
    assert gen_phys.pg_drt0255_cfg() == []
    monkeypatch.setenv("OT_PG_TRACK_TRUTH_MODE", "region")
    assert "export OT_PG_TRACK_TRUTH_MODE = region" in gen_phys.pg_drt0255_cfg()
    monkeypatch.setenv("OT_PG_PAIR_ROW_KEEPOUT", "1")
    assert "export OT_PG_PAIR_ROW_KEEPOUT = 1" in "\n".join(gen_phys.pg_drt0255_cfg())
    monkeypatch.setenv("OT_PG_TRACK_TRUTH_MODE", "obs")
    assert "region" not in "\n".join(gen_phys.pg_drt0255_cfg())
