"""Compare descriptor coordinates to an independent tensor-index formula."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('interleave', [1, 3, 5])
@pytest.mark.parametrize('pass_first,compact', [(0, 0), (1, 0), (1, 1)])
def test_weight_layout_cursor(tmp_path, interleave, pass_first, compact):
    bench = tmp_path / 'tb.sv'
    bench.write_text(r'''
module tb;
parameter integer INTERLEAVE=3;
parameter bit PASS_FIRST=0;
parameter bit COMPACT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,coordinate_ready=0;
reg [31:0] command_generation=11;
reg [15:0] command_rows,command_cols,command_depth;
reg [63:0] command_element_base;
reg [31:0] command_column_stride,command_k_stride;
wire command_ready,coordinate_valid,last,command_error;
wire [31:0] generation,lane_stride;
wire [63:0] element_base;
wire [7:0] lane_mask;
wire [15:0] row_index,column_base,k_index;
ot_a3_weight_layout_cursor #(.INTERLEAVE(INTERLEAVE),.PASS_FIRST(PASS_FIRST),.COMPACT_PASS_REUSE(COMPACT)) dut(.*);
integer checks=0,ticks=0,stage;
always @(posedge clk)begin ticks<=ticks+1;if(ticks>1000000)$fatal(1,"timeout");end
reg held=0;
reg [184:0] payload;
wire [184:0] current_payload={generation,lane_stride,element_base,lane_mask,row_index,column_base,k_index,last};
always @(posedge clk)begin
 if(clear || !rst_n)held<=0;
 else begin
  if(held && (!coordinate_valid || payload!==current_payload))$fatal(1,"unstable stalled coordinate");
  held<=coordinate_valid && !coordinate_ready;payload<=current_payload;
 end
end
task launch(input integer m,n,d,input [63:0] b,input [31:0] s0,s1);
 begin
  @(negedge clk);if(!command_ready)$fatal(1,"not ready");
  command_rows=m;command_cols=n;command_depth=d;command_element_base=b;
  command_column_stride=s0;command_k_stride=s1;command_valid=1;
  @(negedge clk);command_valid=0;
 end
endtask
task cancel;
 begin @(negedge clk);clear=1;coordinate_ready=0;
 #1;if(coordinate_valid || command_ready)$fatal(1,"clear publication");
 @(negedge clk);clear=0;command_generation=command_generation+1;
 end
endtask
task run(input integer m,n,d,input [63:0] b,input [31:0] s0,s1);
 integer r,p,k,c,l,g,stop,outer,inner,passes;
 reg [63:0] expected;
 begin
  launch(m,n,d,b,s0,s1);g=(n+7)/8;passes=(g+INTERLEAVE-1)/INTERLEAVE;
  for(outer=0;outer<(PASS_FIRST?passes:m);outer=outer+1)
  for(inner=0;inner<(PASS_FIRST?m:passes);inner=inner+1)begin
   r=PASS_FIRST?inner:outer;p=(PASS_FIRST?outer:inner)*INTERLEAVE;
   stop=(p+INTERLEAVE<g)?p+INTERLEAVE:g;
   if(!(COMPACT && (stop-p)*d<=1024 && r>0))begin
   for(k=0;k<d;k=k+1)begin
   stop=(p+INTERLEAVE<g)?p+INTERLEAVE:g;
   for(c=p;c<stop;c=c+1)begin
    while(!coordinate_valid)begin @(negedge clk);if(command_error)$fatal(1,"unexpected error");end
    // Ready stalls vary independently of the geometry.
    repeat((checks*7)%4)@(negedge clk);
    expected=b+64'(8*c)*64'(s0)+64'(k)*64'(s1);
    if(element_base!==expected || row_index!=r || column_base!=8*c || k_index!=k ||
       generation!=command_generation || lane_stride!=s0)$fatal(1,"coordinate mismatch %0d",checks);
    for(l=0;l<8;l=l+1)if(lane_mask[l]!=(8*c+l<n))$fatal(1,"tail mask");
    if(last!=((r==m-1 || (COMPACT && (stop-p)*d<=1024)) && c==g-1 && k==d-1))$fatal(1,"last");
    coordinate_ready=1;@(negedge clk);coordinate_ready=0;checks=checks+1;
   end
  end
  end
  end
  if(coordinate_valid || !command_ready)$fatal(1,"completion");
 end
endtask
task reject(input integer m,n,d,input [63:0] b,input [31:0] s0,s1);
 begin
  launch(m,n,d,b,s0,s1);
  repeat(6)begin @(negedge clk);if(coordinate_valid)$fatal(1,"invalid command published");end
  if(!command_error || command_ready)$fatal(1,"missing sticky refusal");cancel();
 end
endtask
initial begin
 repeat(2)@(negedge clk);rst_n=1;
 run(3,53,9,7,111,2);run(2,24,4,19,1,80);run(2,1,7,0,0,0);
 run(6,53,160,11,325,2); // Above whole-row replay capacity; includes partial final pass.
 run(3,53,341,11,687,2);run(3,53,342,11,689,2);
 run(2,9,1024,0,2048,1);
 run(1,65535,1,13,32'hffffffff,1);run(1,1,65535,17,1,32'hffffffff);
 run(1,9,2,64'hffffffffffffff00,16,3);
 run(1,9,2,64'hffffffffffffff7c,16,3); // last active element is exactly UINT64_MAX
 reject(1,9,2,64'hfffffffffffffff0,16,3);
 reject(0,1,1,0,1,1);reject(1,0,1,0,1,1);reject(1,1,0,0,1,1);
 // Both extent products are maximal; addition and final carry must remain exact.
 launch(1,65535,65535,64'hffffffffffffffff-64'd2*64'd65534*64'hffffffff,32'hffffffff,32'hffffffff);
 wait(coordinate_valid);if(command_error)$fatal(1,"maximal combined extent rejected");cancel();
 reject(1,65535,65535,64'hffffffffffffffff-64'd2*64'd65534*64'hffffffff+1,32'hffffffff,32'hffffffff);
 // Revoke an outstanding stalled coordinate and reuse a new generation.
 launch(2,53,5,100,51,2);wait(coordinate_valid);repeat(4)@(negedge clk);cancel();
 run(1,17,3,29,7,3);
 // Cancel at every partial-product/combine/bound admission stage.
 for(stage=0;stage<5;stage=stage+1)begin
  launch(1,9,3,0,3,1);repeat(stage)@(negedge clk);cancel();run(1,8,1,3,1,1);
 end
 $display("PASS layout cursor checks=%0d",checks);$finish;
end
endmodule
''')
    image = tmp_path / 'sim'
    subprocess.run(['iverilog', '-g2012', f'-Ptb.INTERLEAVE={interleave}',
                    f'-Ptb.PASS_FIRST={pass_first}',
                    f'-Ptb.COMPACT={compact}',
                    '-s', 'tb', '-o', str(image),
                    str(ROOT / 'rtl/abi3/ot_a3_weight_layout_cursor.sv'), str(bench)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(['vvp', str(image)], check=True, capture_output=True,
                            text=True, timeout=60)
    assert 'PASS layout cursor checks=' in result.stdout
