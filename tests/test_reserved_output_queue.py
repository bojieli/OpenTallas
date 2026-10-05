"""Reservations cover delayed results, finite capacity, drain and cancellation."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("depth", [1, 2, 3, 4, 8])
def test_reserved_output_queue(tmp_path, depth):
    bench = tmp_path / "tb.sv"
    bench.write_text(
        """module tb;
localparam DEPTH=DEPTH_VALUE;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,reserve_valid=0,stop_producer=0,push_valid=0,out_ready=0;
reg [31:0] push_data=0;
wire reserve_ready,out_valid,empty,protocol_error;
wire [31:0] out_data;
ot_a3_reserved_output_queue #(.WIDTH(32),.DEPTH(DEPTH)) dut(.*);
integer writes=0,reads=0,pending=0,seed=9274,cycles=0;
reg held=0;reg [31:0] held_data;
always @(posedge clk)if(rst_n)begin
 if(held && (!out_valid || out_data!=held_data))$fatal(1,"unstable stalled output");
 held=out_valid && !out_ready;held_data=out_data;
 if(out_valid && out_ready)begin
  if(out_data!=reads)$fatal(1,"lost or reordered output");reads=reads+1;
 end
end
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
initial begin
 tick();rst_n=1;tick();
 // Fill all reservations before any result exists. No overbooking allowed.
 reserve_valid=1;repeat(DEPTH)tick();reserve_valid=0;
 if(reserve_ready || !empty)$fatal(1,"reservation capacity");
 repeat(9)tick();
 push_valid=1;
 for(integer i=0;i<DEPTH;i=i+1)begin push_data=writes;writes=writes+1;tick();end
 push_valid=0;
 repeat(10)tick();
 if(reserve_ready || empty)$fatal(1,"queued capacity");
 // stop releases unused reservations, never drops already queued writes.
 stop_producer=1;tick();stop_producer=0;out_ready=1;repeat(DEPTH)tick();out_ready=0;
 if(!empty || !reserve_ready || reads!=writes)$fatal(1,"drain");
 // Repeated random reserve/result/consumer timing, including simultaneous events.
 repeat(1000)begin
  reserve_valid=($random(seed)&3)!=0;
  out_ready=($random(seed)&7)<4;
  push_valid=(pending>0) && (($random(seed)&3)!=0);
  push_data=writes;
  if(push_valid)begin pending=pending-1;writes=writes+1;end
  if(reserve_valid && reserve_ready)pending=pending+1;
  tick();
  if(protocol_error)$fatal(1,"protocol fault on legal traffic");
 end
 reserve_valid=0;out_ready=1;
 while(pending>0)begin push_valid=1;push_data=writes;writes=writes+1;pending=pending-1;tick();end
 push_valid=0;repeat(DEPTH+2)tick();
 if(!empty || reads!=writes)$fatal(1,"random drain");
 // Abandon a reserved result after producer stop, restoring all credits.
 reserve_valid=1;tick();reserve_valid=0;stop_producer=1;tick();stop_producer=0;#1;
 if(!reserve_ready || !empty)$fatal(1,"abandoned reservation");
 // An unreserved result is refused, reported, and cannot corrupt storage.
 push_valid=1;tick();push_valid=0;
 if(!protocol_error || !empty || reserve_ready)$fatal(1,"unreserved result accepted");
 $display("PASS reserved output queue");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
""".replace("DEPTH_VALUE", str(depth))
    )
    image = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(image),
            str(ROOT / "rtl/abi3/ot_a3_reserved_output_queue.sv"),
            str(bench),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["vvp", str(image)], check=True, capture_output=True, text=True, timeout=30
    )
    assert "PASS reserved output queue" in result.stdout
