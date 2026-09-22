"""Run qualified lane vectors with operand-credit bubbles before memory issue."""

from pathlib import Path
import shutil
import subprocess

import pytest

from tools.rtl_abi3_lane_campaign import RTL_SOURCES

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("corpus", ["d1", "groups"])
@pytest.mark.parametrize("stages", [1, 3])
def test_credit_stalls_preserve_lane_contract(tmp_path, corpus, stages):
    top = (ROOT / "rtl/test/a3_lane_pipelined_top.sv").read_text()
    top = top.replace(
        "    ot_a3_lane_pipelined #(",
        """
    reg [15:0] credit_tick = 0;
    reg [15:0] credit_lfsr = 16'hbeef;
    always @(posedge clk) begin
        if (!rst_n || start_dut) begin
            credit_tick <= 0;
            credit_lfsr <= 16'hbeef;
        end else begin
            credit_tick <= credit_tick + 1'b1;
            credit_lfsr <= {credit_lfsr[14:0], credit_lfsr[15] ^ credit_lfsr[13] ^ credit_lfsr[12] ^ credit_lfsr[10]};
        end
    end
    // Long initial starvation, periodic multi-cycle gaps and pseudo-random
    // single-cycle bubbles exercise issue, recurrence bypass and pipeline drain.
    wire operand_credit = credit_tick > 80 && credit_tick[5:0] < 40 && credit_lfsr[0];
    reg prior_credit = 0;
    integer blocked_cycles = 0;
    always @(posedge clk) begin
        prior_credit <= operand_credit;
        if (rst_n && dut_busy && !operand_credit) blocked_cycles <= blocked_cycles + 1;
    end
    always @(negedge clk) begin
        if (rst_n && d_a_en && !prior_credit) $fatal(1, "read issued without credit");
    end
    final begin
        if (blocked_cycles == 0) $fatal(1, "no credit stalls exercised");
        $display("CREDIT_STALLS %0d", blocked_cycles);
    end
    ot_a3_lane_pipelined #(""",
    )
    top = top.replace(
        ".ACC_SLOTS(ACC_SLOTS)", ".ACC_SLOTS(ACC_SLOTS), .OPERAND_CREDITS(1)"
    )
    top = top.replace(
        ".start(start_dut),", ".start(start_dut), .operand_credit(operand_credit),"
    )
    (tmp_path / "top.sv").write_text(top)
    generated = subprocess.run(
        [
            "python3",
            str(ROOT / "tools/build_abi3_lane_vectors.py"),
            "--suite",
            corpus,
            "--out-dir",
            str(tmp_path),
            "--adder-stages",
            str(stages),
            "--profile",
            "quick",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    compile_result = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb_a3_lane_pipelined",
            f"-Ptb_a3_lane_pipelined.ADDER_STAGES={stages}",
            "-o",
            str(tmp_path / "sim"),
            *[
                str(ROOT / p)
                for p in (
                    *RTL_SOURCES,
                    "rtl/proto/ot_fp32_add_rne_pipe.sv",
                    "rtl/proto/ot_fp32_mul_rne_pipe.sv",
                )
            ],
            str(tmp_path / "top.sv"),
            str(ROOT / "rtl/test/tb_a3_lane_pipelined.sv"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    result = subprocess.run(
        ["vvp", str(tmp_path / "sim")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
    )
    (tmp_path / "simulation.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout, result.stdout
    assert "PASS: ABI3 pipelined lane" in result.stdout
    assert "CREDIT_STALLS" in result.stdout
