"""Check the compressor tree against exact full-width multiplication."""

from pathlib import Path
import os
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("simulator", ["iverilog", "verilator"])
@pytest.mark.parametrize("largest_chunk", [16, 32])
@pytest.mark.parametrize(
    "wa,wb,low", [(163, 161, 160), (163, 163, 160), (162, 170, 320)]
)
def test_balanced_multiplier_exact_product(tmp_path, largest_chunk, wa, wb, low, simulator):
    executable = os.environ.get("VERILATOR", "verilator") if simulator == "verilator" else simulator
    if shutil.which(executable) is None:
        pytest.skip(f"{executable} unavailable")
    # Reuse the adversarial product corpus, including overflow/headroom and
    # discarded-bit checks. The 32-bit variant exercises the deepest tree.
    bench = (ROOT / "rtl/test/tb_wide_mul_seq_equiv.sv").read_text()
    bench = bench.replace("ot_wide_mul_seq #", "ot_wide_mul_tree_seq #")
    bench = bench.replace(".BITS_PER_STEP(16)", f".BITS_PER_STEP({largest_chunk})")
    bench = bench.replace("integer WA = 163", f"integer WA = {wa}")
    bench = bench.replace("integer WB = 161", f"integer WB = {wb}")
    bench = bench.replace("integer LOW = 160", f"integer LOW = {low}")
    # Compare the complete public transaction timing as well as the independent
    # full-width arithmetic oracle. Identical done/busy timing is required for
    # replacing the multiplier inside the certifying exponential controllers.
    reference = """
    wire [DUTS-1:0] ref_busy, ref_done, ref_low;
    wire [HIGH_W-1:0] ref_high [0:DUTS-1];
    genvar r;
    generate for (r=0; r<DUTS; r=r+1) begin : reference
        localparam integer CHUNK = r == 3 ? LARGEST : (2 << r);
        ot_wide_mul_seq #(.WA(WA), .WB(WB), .BITS_PER_STEP(CHUNK), .LOW_BITS(LOW))
            chain (.clk(clk), .rst_n(rst_n), .start(start), .a(a), .b(b),
                   .busy(ref_busy[r]), .done(ref_done[r]),
                   .product_high(ref_high[r]), .low_nonzero(ref_low[r]));
        always @(negedge clk) if (rst_n) begin
            if (busy[r] !== ref_busy[r] || done[r] !== ref_done[r])
                $fatal(1, "tree/chain handshake mismatch at chunk %0d", CHUNK);
            if (done[r] && (product_high[r] !== ref_high[r] ||
                            low_nonzero[r] !== ref_low[r]))
                $fatal(1, "tree/chain result mismatch at chunk %0d", CHUNK);
        end
    end endgenerate
    """.replace("LARGEST", str(largest_chunk))
    bench = bench.replace("endmodule", reference + "\nendmodule")
    source = tmp_path / "tb.sv"
    source.write_text(bench)
    sim = tmp_path / "sim.vvp"
    sources = [str(ROOT / "rtl/lib/ot_wide_mul_tree_seq.sv"),
               str(ROOT / "rtl/lib/ot_wide_mul_seq.sv"), str(source)]
    if simulator == "iverilog":
        command = [executable, "-g2012", "-s", "tb_wide_mul_seq_equiv",
                   "-o", str(sim), *sources]
        run_command = ["vvp", str(sim)]
    else:
        obj = tmp_path / "obj"
        command = [executable, "--binary", "--timing", "-j", "2", "-Wno-fatal",
                   "--top-module", "tb_wide_mul_seq_equiv", "--Mdir", str(obj), *sources]
        run_command = [str(obj / "Vtb_wide_mul_seq_equiv")]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=300)
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run(
        run_command,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout
    count = 127 + 2 * ((wb + 7) // 8)
    assert (
        f"PASS tb_wide_mul_seq_equiv {count} products x 4 chunk widths" in result.stdout
    )
