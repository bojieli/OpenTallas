"""HEAD-97 F1c XO_HOP: ot_s81hd_tile / _native x / go / xv stages between x_q and u_xo (default 0 = unchanged).

Static contract always runs; the Verilator mini bench (tools/s81_head/hd_tile_bench.sh) runs XO_HOP 0 and 2 plus the
GO_DROP mutant when OT_HD_TILE_BENCH=1 and the bench images / Verilator are present (slow, ~minutes).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TILES = ["rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_tile_native.sv"]
TB = "rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv"
BENCH = "tools/s81_head/hd_tile_bench.sh"


def _src(p):
    return (ROOT / p).read_text()


@pytest.mark.parametrize("p", TILES)
def test_tile_xo_hop_default_zero_and_chained(p):
    t = _src(p)
    assert re.search(r"parameter\s+integer\s+XO_HOP\s*=\s*0\b", t), "XO_HOP must default to 0 (unchanged)"
    # stage 0 is the W pin register; u_xo, goo_q and xvo_q read the last stage, so go / xv travel with x
    assert "assign xch[511:0] = x_q;" in t and "assign gch[0] = go_q;" in t and "assign vch[0] = xv_q;" in t
    assert re.search(r"u_xo\s*\(.*\.d\(xch\[512\*XO_HOP \+: 512\]\)", t)
    assert "goo_q <= gch[XO_HOP]; xvo_q <= vch[XO_HOP];" in t
    assert re.search(r"for \(xk = 0; xk < XO_HOP; xk = xk \+ 1\) begin : g_xoh", t)
    assert "u_xoh (.clk(ck), .d(xch[512*xk +: 512]), .q(xch[512*(xk+1) +: 512]))" in t
    # no direct x_q -> u_xo bypass left
    assert ".d(x_q), .q(xo_q)" not in t


def test_tile_and_native_stage_blocks_identical():
    def blk(t):
        a = t.index("// XO_HOP stages")
        return t[a:t.index("ot_s81hd_kreg #(.W(512)) u_xo", a)]
    assert blk(_src(TILES[0])) == blk(_src(TILES[1]))


def test_bench_and_tb_pass_xoh():
    assert "-GXOH=$XOH" in _src(BENCH)
    tb = _src(TB)
    assert re.search(r"parameter\s+integer\s+XOH\s*=\s*0", tb)
    assert tb.count(".XO_HOP(XOH)") == 2


def _bench_ready():
    img = ROOT / "results/rtl/s81_head_tile_1021/img"
    v = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
    return os.environ.get("OT_HD_TILE_BENCH") == "1" and img.is_dir() and (v.exists() or shutil.which("verilator"))


def _bench(tmp, scen, mut, xoh):
    env = dict(os.environ, XOH=str(xoh))
    r = subprocess.run(["bash", BENCH, str(tmp / f"x{xoh}_{mut}"), scen, mut], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=3600)
    return r.returncode, r.stdout.strip().splitlines()[-1:]


@pytest.mark.skipif(not _bench_ready(), reason="OT_HD_TILE_BENCH=1 + images + Verilator 5.050 needed")
@pytest.mark.parametrize("xoh", [0, 2])
def test_bench_all_scenarios_pass(tmp_path, xoh):
    rc, last = _bench(tmp_path, "ALL", "none", xoh)
    assert rc == 0 and last and last[0].startswith("BENCH_PASS"), last


@pytest.mark.skipif(not _bench_ready(), reason="OT_HD_TILE_BENCH=1 + images + Verilator 5.050 needed")
def test_bench_go_drop_mutant_caught_through_stages(tmp_path):
    rc, last = _bench(tmp_path, "A", "GO_DROP", 2)
    assert rc != 0 and last and last[0].startswith("BENCH_FAIL"), last
