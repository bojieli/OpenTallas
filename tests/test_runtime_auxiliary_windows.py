"""Runtime auxiliary SRAM ownership, rebasing, reuse and response stability."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_runtime_auxiliary_windows(tmp_path):
    bench = tmp_path / "tb.sv"
    bench.write_text("""module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,window_valid=0,fill_valid=0,request_valid=0,response_ready=0;
reg [1:0] window_plane=0,fill_plane=0;
reg [31:0] window_generation=7,window_base=0,fill_generation=7;
reg [8:0] window_words=0,fill_index=0;
reg [63:0] fill_data=0;
reg [31:0] request_generation=7,request_a=0,request_s=0,request_ws=0,request_w=0;
reg request_scale_a=0,request_scale_b=0;
wire window_ready,fill_ready,request_ready,response_valid,protocol_error;
wire [2:0] missing_planes;
wire [31:0] response_generation,response_w,response_s_data;
wire [63:0] response_a_data,response_ws_data;
ot_a3_runtime_auxiliary_windows dut(.*);
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task reset_windows;begin clear=1;tick();clear=0;tick();end endtask
task load(input [1:0] plane,input [31:0] base,input [8:0] n,input [63:0] data);begin
 window_plane=plane;window_base=base;window_words=n;window_valid=1;#1;
 if(!window_ready)$fatal(1,"window refused");tick();window_valid=0;
 fill_plane=plane;fill_valid=1;
 for(integer j=0;j<n;j=j+1)begin
  fill_index=9'(j);fill_data=data+64'(j);#1;
  if(!fill_ready)$fatal(1,"fill refused");
  if(dut.resident[plane])$fatal(1,"partially filled window visible");
  tick();
 end
 fill_valid=0;tick();
end endtask
task read_check(input [63:0] a,input [31:0] s,input [63:0] w);begin
 request_valid=1;#1;if(!request_ready)$fatal(1,"resident read stalled");tick();request_valid=0;
 repeat(5)begin
  if(!response_valid || response_a_data!=a || response_s_data!=s || response_ws_data!=w || response_generation!=7 || response_w!=request_w)
   $fatal(1,"wrong held bundle");
  tick();
 end
 // Even a different plane cannot replace SRAM while the response is held.
 window_valid=1;window_plane=0;window_base=999;window_words=1;#1;
 if(window_ready)$fatal(1,"replacement crossed pending read");window_valid=0;
 response_ready=1;tick();response_ready=0;request_w=request_w+1;
end endtask
initial begin
 tick();rst_n=1;tick();request_a=1000;
 if(missing_planes!=1)$fatal(1,"uninitialized window hit");
 load(0,1000,256,64'h100000000);
 // Consecutive synchronous SRAM reads replace responses at one per cycle.
 request_valid=1;response_ready=1;
 for(integer j=0;j<32;j=j+1)begin
  request_a=1000+32'(j);request_w=32'(j);#1;
  if(!request_ready)$fatal(1,"resident read throughput bubble");tick();
  if(!response_valid || response_a_data!=64'h100000000+64'(j) || response_w!=32'(j))$fatal(1,"stream read mismatch");
 end
 request_valid=0;tick();response_ready=0;
 request_a=1255;read_check(64'h1000000ff,0,0);
 request_a=1256;#1;if(request_ready || missing_planes!=1)$fatal(1,"upper bound alias");
 request_a=999;#1;if(request_ready)$fatal(1,"lower bound alias");
 request_a=1001;request_scale_a=1;request_scale_b=1;request_s=42;request_ws=9000;
 load(1,40,3,64'h12340000);load(2,9000,1,64'habcdef);
 read_check(64'h100000001,32'h12340002,64'habcdef);
 // Disabling scale planes must never leak a previous response's scale values.
 request_scale_a=0;request_scale_b=0;read_check(64'h100000001,0,0);
 request_scale_a=1;request_scale_b=1;
 // Replace activation only; scale windows remain resident.
 load(0,70000,2,64'h700);request_a=70001;read_check(64'h701,32'h12340002,64'habcdef);
 request_generation=8;#1;if(request_ready || missing_planes!=7)$fatal(1,"stale generation hit");request_generation=7;
 // Address space end is valid; crossing it must fail before memory writes.
 load(0,32'hffffffff,1,64'h123);request_a=32'hffffffff;read_check(64'h123,32'h12340002,64'habcdef);
 window_valid=1;window_base=32'hffffffff;window_words=2;#1;
 if(window_ready)$fatal(1,"overflow admitted");tick();window_valid=0;
 if(!protocol_error)$fatal(1,"overflow not reported");reset_windows();
 // Incomplete and out-of-order fills never publish a window.
 window_base=0;window_words=2;window_valid=1;tick();window_valid=0;
 fill_plane=0;fill_index=1;fill_valid=1;#1;
 if(fill_ready)$fatal(1,"misordered fill accepted");tick();fill_valid=0;
 if(!protocol_error || dut.resident!=0)$fatal(1,"misordered fill visible");reset_windows();
 window_valid=1;tick();window_valid=0;fill_index=0;fill_generation=6;fill_valid=1;#1;
 if(fill_ready)$fatal(1,"stale fill accepted");tick();fill_valid=0;
 if(!protocol_error)$fatal(1,"stale fill not reported");reset_windows();
 // Invalid plane/count descriptor refuses without exposing memory.
 window_plane=3;window_valid=1;#1;if(window_ready)$fatal(1,"invalid plane");tick();window_valid=0;
 if(!protocol_error)$fatal(1,"invalid plane not reported");reset_windows();
 window_plane=0;window_words=0;window_valid=1;#1;if(window_ready)$fatal(1,"zero extent");tick();window_valid=0;
 if(!protocol_error)$fatal(1,"zero extent not reported");reset_windows();
 fill_generation=7;load(0,0,1,64'hcafe);request_a=0;request_scale_a=0;request_scale_b=0;
 request_valid=1;tick();request_valid=0;
 if(!response_valid)$fatal(1,"missing pre-clear response");reset_windows();
 if(response_valid || request_ready || dut.resident!=0)$fatal(1,"clear retained stale response");
 $display("PASS runtime auxiliary windows");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
""")
    image = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-DOT_A3_FAKERAM_BEHAVIOURAL",
            "-s",
            "tb",
            "-o",
            str(image),
            str(ROOT / "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv"),
            str(ROOT / "rtl/abi3/ot_a3_runtime_auxiliary_windows.sv"),
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
    assert "PASS runtime auxiliary windows" in result.stdout
