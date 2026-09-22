"""Completion must follow both transport drain and committed output writes."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_runtime_completion_barrier(tmp_path):
    bench = tmp_path / "tb.sv"
    bench.write_text("""module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0,compute_done=0,service_fault=0,abort_valid=0,transport_ack=0,writes_drained=0,completion_ready=0;
reg [31:0] command_generation=7;reg [7:0] compute_error=0;
wire start_ready,transport_cancel,service_clear,compute_abort,busy,completion_valid;
wire [31:0] transport_generation,completion_generation;
wire [7:0] completion_error;
ot_a3_runtime_operation_lifetime dut(.*);
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task launch(input [31:0] tag);begin
 if(!start_ready)$fatal(1,"not idle");command_generation=tag;start=1;tick();start=0;command_generation=99;
 if(!busy || start_ready)$fatal(1,"ownership missing");
end endtask
task complete_check(input [31:0] tag,input [7:0] err);begin
 if(!completion_valid || completion_generation!=tag || completion_error!=err)$fatal(1,"wrong completion");
 repeat(5)begin tick();if(!completion_valid || !busy || start_ready || completion_generation!=tag || completion_error!=err)$fatal(1,"completion not held");end
 completion_ready=1;tick();completion_ready=0;if(busy || !start_ready)$fatal(1,"ownership not released");
end endtask
initial begin
 tick();rst_n=1;tick();launch(7);
 // Idle-looking acknowledgements during RUN must not count as drain.
 transport_ack=1;writes_drained=1;repeat(3)tick();transport_ack=0;writes_drained=0;
 compute_done=1;compute_error=8'd3;tick();compute_done=0;
 if(!transport_cancel || !service_clear || compute_abort || completion_valid)$fatal(1,"normal drain entry");
 start=1;repeat(3)tick();start=0;if(transport_generation!=7)$fatal(1,"busy start overwrote generation");
 transport_ack=1;tick();transport_ack=0;repeat(3)tick();
 if(transport_cancel || completion_valid)$fatal(1,"did not wait for writes");
 writes_drained=1;tick();complete_check(7,3);
 // Opposite acknowledgement order and service-fault priority.
 writes_drained=0;launch(8);service_fault=1;compute_done=1;tick();service_fault=0;compute_done=0;
 if(!compute_abort || !service_clear)$fatal(1,"fault did not stop compute/service");
 writes_drained=1;repeat(4)tick();if(completion_valid)$fatal(1,"transport not drained");
 transport_ack=1;tick();transport_ack=0;complete_check(8,8'hfe);
 writes_drained=0;launch(9);abort_valid=1;tick();abort_valid=0;
 transport_ack=1;writes_drained=1;tick();transport_ack=0;complete_check(9,8'hff);
 launch(10);rst_n=0;#1;if(busy || transport_cancel || completion_valid || compute_abort)$fatal(1,"reset credits");
 tick();rst_n=1;tick();if(!start_ready)$fatal(1,"reset ownership");
 $display("PASS lifetime drain ordering, generation, fault priority, completion stalls and reset");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
""")
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_runtime_operation_lifetime.sv"),
            str(bench),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS lifetime" in run.stdout
