"""C-FENCE-GEOM-ILLEGAL (R3-FENCE 11-27): every generated fence / region box snaps OUTWARD onto the site / row grid."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import logic_cluster as LC  # noqa: E402

ROOT = HERE.parent.parent
FILES = ["physical/common_flow/pin_reg_face_fence.tcl", "tools/die_plan/region_guide.tcl", "tools/die_plan/serdes_lanes.tcl",
         "physical/die_plan/qwen_kvsys/cores/harden/zone_fence.tcl", "physical/die_plan/qwen_kvsys/cores/harden/head_lane_fence.tcl"]
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")

# 4000 dbu / um; site 0.054 um = 216, row 0.27 um = 1080; core (4.32 um = 17280 dbu) .. (100 um)
MOCK = """
namespace eval ord {}
set ::lc_u 4000
proc ord::get_db_block {} { return blk }
proc blk {m} { switch $m { getRows { return {row} } getCoreArea { return core } } }
proc row {m} { return site }
proc site {m} { switch $m { getWidth { return 216 } getHeight { return 1080 } } }
proc core {m} { switch $m { xMin { return 17280 } yMin { return 17280 } xMax { return 400000 } yMax { return 400000 } } }
"""


def snap_proc(src):
    m = re.search(r"^proc ot_fence_snap \{.*?^\}\n", src, re.S | re.M)
    assert m, "ot_fence_snap missing"
    return m.group(0)


def run(script):
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert not r.stderr.strip(), r.stderr
    return r.stdout.split()


def test_every_emitter_snaps_and_the_proc_is_identical():
    procs = set()
    for f in FILES:
        src = (ROOT / f).read_text()
        procs.add(snap_proc(src))
        for ln in src.splitlines():
            if "dbBox_create" in ln and "$reg" in ln or "dbBox_create $r " in ln or "dbBox_create $rg " in ln:
                assert "ot_fence_snap" in ln, (f, ln)
    assert len(procs) == 1


@needs_tcl
@pytest.mark.parametrize("f", FILES)
def test_snap_is_outward_and_idempotent(f):
    proc = snap_proc((ROOT / f).read_text())
    # already on the grid -> unchanged (byte-identical)
    on = [17280 + 216 * 3, 17280 + 1080 * 2, 17280 + 216 * 50, 17280 + 1080 * 9]
    assert run(MOCK + proc + "puts [ot_fence_snap %s]" % " ".join(map(str, on))) == list(map(str, on))
    # the HEAD East shape: edges 0.016 / 0.034 um (64 / 136 dbu) off the grid -> outward by < 1 site / row, never inward
    off = [17280 + 216 * 3 + 64, 17280 + 1080 * 2 + 136, 17280 + 216 * 50 - 64, 17280 + 1080 * 9 - 136]
    got = [int(v) for v in run(MOCK + proc + "puts [ot_fence_snap %s]" % " ".join(map(str, off)))]
    assert got == [17280 + 216 * 3, 17280 + 1080 * 2, 17280 + 216 * 50, 17280 + 1080 * 9]
    assert got[0] <= off[0] and got[1] <= off[1] and got[2] >= off[2] and got[3] >= off[3]
    # an edge inside the core is never pushed past the core edge
    got = [int(v) for v in run(MOCK + proc + "puts [ot_fence_snap 20000 20000 399999 399999]")]
    assert got[2] <= 400000 and got[3] <= 400000


@needs_tcl
def test_logic_cluster_box_matches_and_is_gated_on_grid():
    body = "\n".join(LC.SNAP_TCL)
    out = [int(v) for v in run(MOCK + body + "\nputs [ot_lc_box 4.3201 4.3201 10.0001 10.0001]")]
    assert out[0] == 17280 and out[1] == 17280          # 4.3201 um = 17280.4 dbu -> round 17280 on grid
    assert out[2] % 216 == 17280 % 216 and out[3] % 1080 == 17280 % 1080
    on = [int(v) for v in run(MOCK + body + "\nputs [ot_lc_box 4.32 4.32 10.152 9.99]")]
    assert on[0] == 17280 and on[2] == 40608 and on[3] % 1080 == 17280 % 1080 and on[3] >= 39960
    assert "ot_lc_box $x0 $y0 $x1 $y1" in "\n".join(LC.REGION_TCL)
