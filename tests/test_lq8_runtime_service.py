"""Runtime service owns the command until clear and surfaces transport faults."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_runtime_service_lifetime(tmp_path):
    bench = tmp_path / "tb.sv"
    bench.write_text("""module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,compute_admitted=0;
reg [31:0] cfg_generation=7;reg [15:0] cfg_depth=2;
reg weight_response_valid=0;
wire command_ready,busy,geometry_error,protocol_error,operand_credit;
wire weight_request_valid,auxiliary_request_valid,weight_response_ready;
wire [63:0] weight_request_tag;
wire [31:0] weight_request_address;
wire [9:0] weight_request_words;
ot_a3_lq8_runtime_operands dut(
.clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(command_valid),.command_ready(command_ready),
.cfg_generation(cfg_generation),.cfg_rows(16'd1),.cfg_cols(16'd8),.cfg_depth(cfg_depth),.cfg_group(8'd1),
.cfg_scale_a(1'b0),.cfg_scale_b(1'b0),.cfg_block_a(16'd0),.cfg_block_b(16'd0),.cfg_block_rows_a(16'd0),
.cfg_a_base(32'd0),.cfg_s_base(32'd0),.cfg_ws_base(32'd0),.cfg_w_base(32'd100),
.compute_admitted(compute_admitted),.operand_request(compute_admitted),.operand_issue(1'b0),
.operand_a(32'd0),.operand_s(32'd0),.operand_ws(32'd0),.operand_w(32'd100),.operand_credit(operand_credit),
.busy(busy),.geometry_error(geometry_error),.protocol_error(protocol_error),
.weight_request_valid(weight_request_valid),.weight_request_ready(1'b0),.weight_request_tag(weight_request_tag),
.weight_request_address(weight_request_address),.weight_request_words(weight_request_words),
.weight_response_valid(weight_response_valid),.weight_response_ready(weight_response_ready),
.weight_response_tag(64'h600000064),.weight_response_index(10'd0),.weight_response_data(128'd0),
.auxiliary_request_valid(auxiliary_request_valid),.auxiliary_request_ready(1'b0),
.auxiliary_response_valid(1'b0),.auxiliary_response_generation(32'd0),.auxiliary_response_w(32'd0),
.auxiliary_response_a_data(64'd0),.auxiliary_response_s_data(32'd0),.auxiliary_response_ws_data(64'd0));
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
initial begin
 tick();rst_n=1;command_valid=1;tick();command_valid=0;cfg_generation=99;cfg_depth=0;
 repeat(24)begin tick();if(!busy || command_ready || weight_request_valid || auxiliary_request_valid)$fatal(1,"unadmitted operation escaped");end
 compute_admitted=1;
 wait(weight_request_valid);@(negedge clk);
 repeat(4)begin
  if(weight_request_tag!={32'd7,32'd100} || weight_request_address!=100 || weight_request_words!=2)$fatal(1,"command not captured");tick();
 end
 // New command while busy cannot change the owned generation.
 command_valid=1;repeat(3)tick();command_valid=0;
 if(weight_request_tag!={32'd7,32'd100})$fatal(1,"busy overwrite");
 weight_response_valid=1;tick();weight_response_valid=0;
 if(!protocol_error || operand_credit || weight_response_ready)$fatal(1,"malformed transport not surfaced");
 repeat(3)tick();if(!protocol_error)$fatal(1,"error not sticky");
 clear=1;#1;if(operand_credit || weight_request_valid || auxiliary_request_valid || command_ready)$fatal(1,"clear left credits");
 tick();clear=0;compute_admitted=0;#1;if(busy || protocol_error || !command_ready)$fatal(1,"clear did not revoke ownership");
 // Invalid geometry holds ownership and never launches external requests.
 command_valid=1;tick();command_valid=0;repeat(22)tick();
 if(!geometry_error || !busy || command_ready || weight_request_valid || auxiliary_request_valid)$fatal(1,"invalid geometry lifecycle");
 clear=1;tick();clear=0;cfg_depth=2;cfg_generation=8;command_valid=1;tick();command_valid=0;compute_admitted=1;
 wait(weight_request_valid);@(negedge clk);
 if(weight_request_tag!={32'd8,32'd100} || geometry_error || protocol_error)$fatal(1,"new generation failed");
 $display("PASS runtime service ownership, admission gate, sticky fault, clear and restart");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
""")
    names = [
        "ot_a3_lq8_runtime_operands",
        "ot_a3_lq8_operand_admission",
        "ot_a3_lq8_operand_cursor",
        "ot_a3_lq8_auxiliary_prefetch",
        "ot_a3_lq8_operand_join",
        "ot_a3_weight_tile_scheduler",
        "ot_a3_weight_tile_prefetch",
        "ot_a3_runtime_weight_banks",
        "ot_a3_operand_bank_owner",
    ]
    sim = tmp_path / "sim"
    result = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(sim),
            *[str(ROOT / "rtl/abi3" / f"{n}.sv") for n in names],
            str(ROOT / "rtl/test/tb_a3_runtime_weight_banks.sv"),
            str(bench),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS runtime service ownership" in run.stdout
