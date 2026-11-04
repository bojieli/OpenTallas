"""DIE-HBM-61/RTL 11-03: face_shell opt-in reset relay (async assert, release after N edges)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_shell as FS  # noqa: E402

W = {"clk": 1, "rst_n": 1, "a": 4, "y": 4}
D = {"clk": "input", "rst_n": "input", "a": "input", "y": "output"}
K = dict(W)


def _shell(rr):
    return FS.emit_shell("top", "top__fcore", {}, W, D, K, {"clk", "rst_n"}, "clk", rst_relay=rr)


def test_emit_off_is_unchanged_passthrough():
    t = _shell(None)
    assert ".rst_n(rst_n)" in t and FS.RCELL not in t


def test_emit_relay_instance():
    t = _shell({"rst_n": 3})
    assert re.search(r"ot_hbm_face_rst_relay #\(\.W\(1\), \.N\(3\)\) u_brst_rst_n \(\.clk\(clk\), \.rst_ni\(rst_n\)", t)
    assert ".rst_n(rst_n__rr)" in t


TB = """
`timescale 1ns/1ps
module tb;
  reg clk = 0, rn = 0; wire q;
  ot_hbm_face_rst_relay #(.W(1), .N(%(N)d)) dut (.clk(clk), .rst_ni(rn), .rst_no(q));
  always #5 clk = ~clk;
  integer e = 0, rel = -1, bad = 0;
  always @(posedge clk) begin e = e + 1; if (q === 1'b1 && rel < 0) rel = e; end
  initial begin
    #23 rn = 1;                       // release between edges 2 and 3 (edges at 5,15,25,...)
    #200;
    #4 rn = 0; #1 if (q !== 1'b0) bad = 1;   // assertion must be immediate (no clock edge)
    $display("REL %%0d BAD %%0d", rel, bad); $finish;
  end
endmodule
"""


def _run(tmp, cell, n):
    (tmp / "c.sv").write_text(cell)
    (tmp / "tb.sv").write_text(TB % {"N": n})
    subprocess.run(["iverilog", "-g2012", "-o", str(tmp / "a.out"), str(tmp / "c.sv"), str(tmp / "tb.sv")], check=True)
    out = subprocess.run(["vvp", "-n", str(tmp / "a.out")], capture_output=True, text=True, check=True).stdout
    m = re.search(r"REL (-?\d+) BAD (\d+)", out)
    return int(m.group(1)), int(m.group(2))


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
@pytest.mark.parametrize("n", [2, 3])
def test_sim_release_after_n_edges_and_async_assert(tmp_path, n):
    rel, bad = _run(tmp_path, FS.RCELL_SV, n)
    # first edge after release is edge 3 (t=25); q rises at edge 3+N-1 and is seen 1 at the next sampled edge
    assert rel == 3 + n and bad == 0


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_sim_mutant_sync_assert_is_caught(tmp_path):
    mut = FS.RCELL_SV.replace("always @(posedge clk or negedge rst_ni[g])", "always @(posedge clk)")
    assert mut != FS.RCELL_SV
    _, bad = _run(tmp_path, mut, 2)
    assert bad == 1


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_sim_mutant_short_chain_is_caught(tmp_path):
    mut = FS.RCELL_SV.replace("assign rst_no[g] = s[N-1];", "assign rst_no[g] = s[N-2];")
    rel, _ = _run(tmp_path, mut, 3)
    assert rel != 3 + 3
