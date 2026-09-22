"""Bounded refill planning, immutable geometry and tagged transport contracts."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("rolling", [0, 1])
def test_auxiliary_window_scheduler(tmp_path, rolling):
    bench = tmp_path / "tb.sv"
    bench.write_text("""module tb;
parameter bit ROLLING=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,request_valid=0,window_ready=0,fill_ready=0,fetch_ready=0,response_valid=0;
reg [31:0] command_generation=7,request_generation=7;
reg [95:0] command_bases=0,command_words=0,request_addresses=0;
reg [2:0] missing_planes=0;
reg [63:0] response_tag=0,response_data=0;
reg [8:0] response_index=0;
wire command_ready,window_valid,fill_valid,fetch_valid,response_ready,active,protocol_error;
wire [1:0] window_plane,fill_plane,fetch_plane;
wire [31:0] window_generation,window_base,fill_generation,fetch_address;
wire [8:0] window_words,fill_index,fetch_words;
wire [63:0] fill_data,fetch_tag;
ot_a3_auxiliary_window_scheduler #(.ACTIVATION_MISS_ALIGNED(ROLLING)) dut(.*);
integer bursts=0,beats=0;
reg [63:0] saved_tag;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task reset_op;begin
 clear=1;request_valid=0;response_valid=0;window_ready=0;fill_ready=0;fetch_ready=0;
 tick();clear=0;tick();
end endtask
task command(input [95:0] bases,input [95:0] words);begin
 command_bases=bases;command_words=words;command_valid=1;#1;
 if(!command_ready)$fatal(1,"command refused");tick();command_valid=0;
 // Live mutation must not alter the operation's captured bounds.
 command_bases=~bases;command_words=0;command_generation=99;
end endtask
task plan(input [1:0] plane,input [31:0] address,input [31:0] base,input [8:0] words);begin
 request_addresses=0;request_addresses[32*plane+:32]=address;
 missing_planes=3'b001<<plane;request_valid=1;
 wait(window_valid);@(negedge clk);request_valid=0;
 repeat(4)begin
  if(!window_valid || window_plane!=plane || window_generation!=7 || window_base!=base || window_words!=words)$fatal(1,"wrong window plan");tick();
 end
 window_ready=1;tick();window_ready=0;
 if(!fetch_valid)$fatal(1,"missing fetch");saved_tag=fetch_tag;
 repeat(3)begin
  if(!fetch_valid || fetch_tag!=saved_tag || fetch_plane!=plane || fetch_address!=base || fetch_words!=words)$fatal(1,"unstable burst");tick();
 end
 fetch_ready=1;tick();fetch_ready=0;response_tag=saved_tag;response_index=0;
 bursts=bursts+1;
end endtask
task fill(input [8:0] words);begin
 for(integer j=0;j<words;j=j+1)begin
  response_index=9'(j);response_data=64'(j)+64'h1234567800000000;response_valid=1;
  fill_ready=0;#1;
  if(response_ready || !fill_valid || fill_index!=9'(j) || fill_data!=response_data || fill_generation!=7)$fatal(1,"fill stall contract");tick();
  fill_ready=1;#1;if(!response_ready)$fatal(1,"matching fill refused");tick();beats=beats+1;
  response_valid=0;fill_ready=0;tick();
 end
 if(protocol_error)$fatal(1,"legal burst faulted");
end endtask
task bad_address(input [31:0] address);begin
 request_valid=1;request_addresses={64'd0,address};missing_planes=1;
 repeat(8)begin tick();if(window_valid || fetch_valid || fill_valid)$fatal(1,"invalid extent fetched");end
 if(!protocol_error)$fatal(1,"invalid address not reported");request_valid=0;
end endtask
initial begin
 tick();rst_n=1;tick();
 command({32'hfffffff0,32'd700,32'd3},{32'd16,32'd1,32'd513});
 // Pages start at the object's base, not at global 256-word boundaries.
 plan(0,3,3,256);fill(256);
 plan(0,258,ROLLING?258:3,256);if(saved_tag!=64'h700000001)$fatal(1,"burst serial did not advance");fill(256);
 plan(0,259,259,256);fill(256);
 plan(0,515,515,1);fill(1);
 plan(1,700,700,1);fill(1);
 plan(2,32'hffffffff,32'hfffffff0,16);fill(16);
 // Priority must preserve the first missing plane.
 request_addresses={32'hfffffff0,32'd700,32'd3};missing_planes=7;request_valid=1;
 wait(window_valid);@(negedge clk);if(window_plane!=0)$fatal(1,"miss priority");reset_op();
 command_generation=7;command(0,{64'd0,32'd2});bad_address(2);reset_op();
 command_generation=7;command({64'd0,32'd100},{64'd0,32'd2});bad_address(99);reset_op();
 command_generation=7;command({64'd0,32'hffffffff},{64'd0,32'd2});bad_address(32'hffffffff);reset_op();
 command_generation=7;command(0,0);bad_address(0);reset_op();
 command_generation=7;command(0,{64'd0,32'd2});plan(0,0,0,2);
 response_valid=1;response_tag=saved_tag^1;response_index=0;fill_ready=1;#1;
 if(fill_valid || response_ready)$fatal(1,"wrong tag accepted");tick();
 if(!protocol_error)$fatal(1,"wrong tag not reported");reset_op();
 command_generation=7;command(0,{64'd0,32'd2});plan(0,0,0,2);
 response_valid=1;response_index=1;fill_ready=1;#1;
 if(fill_valid || response_ready)$fatal(1,"wrong index accepted");tick();
 if(!protocol_error)$fatal(1,"wrong index not reported");reset_op();
 // Clear cancels an in-progress fill and prevents any later beat publication.
 command_generation=7;command(0,{64'd0,32'd2});plan(0,0,0,2);reset_op();
 response_valid=1;#1;if(fill_valid || response_ready)$fatal(1,"late response accepted");tick();
 if(!protocol_error)$fatal(1,"unsolicited response not reported");reset_op();
 command_generation=7;command(0,{64'd0,32'd2});request_generation=8;request_valid=1;missing_planes=1;tick();
 if(!protocol_error || window_valid)$fatal(1,"stale request accepted");
 $display("PASS auxiliary window scheduler bursts=%0d beats=%0d",bursts,beats);$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
""")
    image = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            f"-Ptb.ROLLING={rolling}",
            "-o",
            str(image),
            str(ROOT / "rtl/abi3/ot_a3_auxiliary_window_scheduler.sv"),
            str(bench),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["vvp", str(image)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS auxiliary window scheduler" in result.stdout
