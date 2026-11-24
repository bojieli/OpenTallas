"""QC-FW-CAP 11-23: ot_dp_dly store-complement relays (OT_DLY_CPL) are inert by default and port-equivalent when on."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402

DLY_RE = re.compile(r"module ot_dp_dly #\(parameter integer W = 1, parameter integer D = 1\).*?endmodule", re.S)


def _dly():
    m = DLY_RE.search(bind.CELLS)
    assert m, "ot_dp_dly missing from bind CELLS"
    return m.group(0)


def test_default_branch_is_the_plain_chain():
    t = _dly()
    assert "`ifdef OT_DLY_CPL" in t and "`else" in t and "`endif" in t
    plain = t.split("`else", 1)[1].split("`endif", 1)[0]
    assert "r[0] <= d;" in plain and "r[i] <= r[i-1];" in plain and "assign q = r[D-1];" in plain
    cpl = t.split("`ifdef OT_DLY_CPL", 1)[1].split("`else", 1)[0]
    assert "r[0] <= ~d;" in cpl and "r[i] <= ~r[i-1];" in cpl and "(D % 2 == 1) ? ~r[D-1] : r[D-1]" in cpl


def _python_model(depth, seq, cpl):
    """Cycle model of the RTL: register k after each clock; returns q per cycle once the pipe is full."""
    r = [0] * depth
    out = []
    for x in seq:
        nr = [(1 - x) if cpl else x] + [((1 - r[i - 1]) if cpl else r[i - 1]) for i in range(1, depth)]
        r = nr
        last = r[depth - 1]
        out.append((1 - last) if (cpl and depth % 2 == 1) else last)
    return out[depth:]


@pytest.mark.parametrize("depth", [1, 2, 3, 6, 7, 9])
def test_model_port_equivalent(depth):
    seq = [(i * 7 + i // 3) % 2 for i in range(64)]
    assert _python_model(depth, seq, True) == _python_model(depth, seq, False)


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog not installed")
def test_iverilog_port_equivalent(tmp_path):
    tb = tmp_path / "tb.sv"
    tb.write_text(_dly().replace("module ot_dp_dly", "module dly_x", 1) + "\n" + """
module tb;
  reg clk = 0; reg [3:0] d = 0; wire [3:0] q1, q6, q7;
  dly_x #(.W(4), .D(1)) u1 (.clk(clk), .d(d), .q(q1));
  dly_x #(.W(4), .D(6)) u6 (.clk(clk), .d(d), .q(q6));
  dly_x #(.W(4), .D(7)) u7 (.clk(clk), .d(d), .q(q7));
  reg [3:0] h [0:15]; integer n, bad;
  initial begin
    bad = 0;
    for (n = 0; n < 64; n = n + 1) begin
      d = $random; h[n % 16] = d; #1 clk = 1; #1 clk = 0;
      if (n >= 8) begin
        if (q1 !== h[n % 16]) bad = bad + 1;
        if (q6 !== h[(n - 5) % 16]) bad = bad + 1;
        if (q7 !== h[(n - 6) % 16]) bad = bad + 1;
      end
    end
    $display("BAD %0d", bad); $finish;
  end
endmodule
""")
    for define in ([], ["-DOT_DLY_CPL"]):
        exe = tmp_path / ("sim" + ("c" if define else "p"))
        subprocess.run(["iverilog", "-g2012", *define, "-o", str(exe), str(tb)], check=True)
        out = subprocess.run(["vvp", str(exe)], check=True, capture_output=True, text=True).stdout
        assert "BAD 0" in out, (define, out)
