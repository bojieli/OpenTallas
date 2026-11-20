"""FABLE-FIX-HEAD-MESH 11-20 PICK_SPLIT: ot_s81hd_bundle(_native) merge picks as compare-register + select.

Static contract always runs.  The differential bench (rtl/dsrom_sys/s81_head/test/tb_s81hd_pick_split.sv: PICK_SPLIT
1 / 2 / 3 against 0 on identical stub element outputs; res_v and {res_row, res_bits} must equal the reference exactly
popcount(PICK_SPLIT) cycles later) runs with Verilator 5.050, plus two mutants it must catch: a wrong lag and a select
with swapped operands.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
D = "rtl/dsrom_sys/s81_head/"
BUNDLES = [D + "ot_s81hd_bundle.sv", D + "ot_s81hd_bundle_native.sv"]
TILES = [D + "ot_s81hd_tile.sv", D + "ot_s81hd_tile_native.sv"]
TB = D + "test/tb_s81hd_pick_split.sv"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
MUX = "assign ps_o[pp][pb] = s_q[pb / 14] ? v_q[pb] : u_q[pb];"


def _src(p):
    return (ROOT / p).read_text()


@pytest.mark.parametrize("p", BUNDLES)
def test_bundle_default_off_and_valid_unchanged(p):
    t = _src(p)
    assert re.search(r"parameter \[1:0\] PICK_SPLIT = 2'b00,", t)
    # valid logic and go block window untouched; res_v only delayed by the split count
    assert "localparam integer GW = 4 + 2 * MERGE_HOP;" in t
    assert "c1_v <= &pk_done_m && !gblk;" in t
    assert "res_v <= PICK_S == 0 ? res_v_n : res_vs[PICK_S == 0 ? 0 : PICK_S - 1];" in t
    # default path keeps the one-cycle picks
    assert "pick(c1_h[0], c1_h[1]);" in t and "pick(pk_h[0], pk_h[1]);" in t
    # kept select copies, one per 14-b slice
    assert "ot_s81hd_kreg #(.W(PICK_NSL)) u_sel" in t and MUX in t


def test_bundle_and_native_merge_blocks_identical():
    def blk(t):
        a = t.index("    function automatic [80:0] pick(")
        return t[a:t.index("    // MERGE_HOP: the five element fault pins", a)]
    assert blk(_src(BUNDLES[0])) == blk(_src(BUNDLES[1]))


@pytest.mark.parametrize("p", TILES)
def test_tile_passes_pick_split(p):
    t = _src(p)
    assert "parameter [1:0] PICK_SPLIT = 2'b00," in t
    assert ".PICK_SPLIT(PICK_SPLIT)" in t


def _run(tmp, mh, lag_err=0, bundle=None):
    bundle = bundle or (ROOT / BUNDLES[1])
    obj = tmp / f"obj_{mh}_{lag_err}"
    c = subprocess.run([str(VERILATOR), "--binary", "--timing", "-j", "2", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                        "--top-module", "tb_s81hd_pick_split", f"-GMH={mh}", f"-GLAG_ERR={lag_err}", "-Mdir", str(obj),
                        str(ROOT / TB), str(bundle), str(ROOT / "rtl/hdc/ot_hdc_delay.sv")],
                       capture_output=True, text=True, timeout=1800)
    assert c.returncode == 0, c.stderr[-2000:]
    r = subprocess.run([str(obj / "Vtb_s81hd_pick_split")], capture_output=True, text=True, timeout=600)
    return r.returncode, [l for l in r.stdout.splitlines() if "PICK_SPLIT_" in l]


need_v = pytest.mark.skipif(not VERILATOR.exists() or not shutil.which("make"), reason="Verilator 5.050 needed")


@need_v
@pytest.mark.parametrize("mh", [1, 0])
def test_bench_split_equals_reference_delayed(tmp_path, mh):
    rc, lines = _run(tmp_path, mh)
    assert rc == 0 and lines and lines[-1].startswith("PICK_SPLIT_PASS"), lines


@need_v
def test_bench_catches_wrong_lag(tmp_path):
    rc, lines = _run(tmp_path, 1, lag_err=1)
    assert rc != 0 and any(l.startswith("PICK_SPLIT_FAIL") for l in lines), lines


@need_v
def test_bench_catches_swapped_select(tmp_path):
    t = _src(BUNDLES[1])
    assert t.count(MUX) == 1
    mut = tmp_path / "ot_s81hd_bundle_native.sv"
    mut.write_text(t.replace(MUX, "assign ps_o[pp][pb] = s_q[pb / 14] ? u_q[pb] : v_q[pb];"))
    rc, lines = _run(tmp_path, 1, bundle=mut)
    assert rc != 0 and any("data" in l for l in lines), lines
