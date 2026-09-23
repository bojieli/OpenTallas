"""Local softmax lane writes preserve every visible cycle of the old controller."""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('lanes', [1, 3, 64, 65])
@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
def test_lane_write_equivalence(tmp_path, lanes, simulator):
    before = tmp_path / 'before.sv'
    before.write_text((ROOT / 'results/rtl/softmax_lane_write/before.sv').read_text().replace(
        'module ot_a3_attention_softmax_block #(', 'module old_softmax #('))
    bench = tmp_path / 'tb.sv'
    bench.write_text(r'''
module ot_a3_fp32_transcendental_cr_rne(
input clk,rst_n,in_valid,operation,out_ready,input [31:0] argument_code,
output in_ready,output reg out_valid,output reg [31:0] result_code,output reg [1:0] result_error);
reg [2:0] delay_left;
assign in_ready=delay_left==0 && !out_valid;
always @(posedge clk) begin
 if(!rst_n)begin delay_left<=0;out_valid<=0;result_code<=0;result_error<=0;end
 else begin
  if(out_valid && out_ready)out_valid<=0;
  if(in_valid && in_ready)begin
   delay_left<=3; result_code<=argument_code ^ 32'h3f800001;
   result_error<=tb.fail_service ? 2'd1 : 2'd0;
  end else if(delay_left!=0)begin
   delay_left<=delay_left-1;
   if(delay_left==1)out_valid<=1;
  end
 end
end
endmodule
module tb;
localparam L=LANES;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0,first=0,fail_service=0;
reg [31:0] running_max=0;
reg [L-1:0] valid_lanes=0;
reg [32*L-1:0] scores=0;
wire [1:0] busy,done;
wire [31:0] maxes[0:1],rescale[0:1],counts[0:1];
wire [32*L-1:0] probs[0:1];
wire [7:0] errors[0:1];
ot_a3_attention_softmax_block #(.LANES(L)) dut(
.clk(clk),.rst_n(rst_n),.start(start),.cfg_first(first),.cfg_running_max(running_max),
.lane_valid(valid_lanes),.scores(scores),.busy(busy[0]),.done(done[0]),
.updated_max(maxes[0]),.rescale(rescale[0]),.probabilities(probs[0]),.error_code(errors[0]),.exp_count(counts[0]));
old_softmax #(.LANES(L)) ref_dut(
.clk(clk),.rst_n(rst_n),.start(start),.cfg_first(first),.cfg_running_max(running_max),
.lane_valid(valid_lanes),.scores(scores),.busy(busy[1]),.done(done[1]),
.updated_max(maxes[1]),.rescale(rescale[1]),.probabilities(probs[1]),.error_code(errors[1]),.exp_count(counts[1]));
integer checked=0;
always @(negedge clk) begin
 #1;
 if({busy[0],done[0],maxes[0],rescale[0],probs[0],errors[0],counts[0]} !==
    {busy[1],done[1],maxes[1],rescale[1],probs[1],errors[1],counts[1]})
    $fatal(1,"visible cycle mismatch lane count %0d cycle %0d",L,checked);
 checked=checked+1;
end
integer t,j;
initial begin
 repeat(3)@(negedge clk);rst_n=1;
 for(t=0;t<24;t=t+1)begin
  @(negedge clk);first=t%3==0;running_max=0;fail_service=t%7==5;
  for(j=0;j<L;j=j+1)begin
   valid_lanes[j]=(t%6==0)?0:((j+t)%4!=0);
   case((j+t)%4)
    0:scores[j*32+:32]=0;
    1:scores[j*32+:32]=32'hbf800000;
    2:scores[j*32+:32]=32'hc0000000;
    3:scores[j*32+:32]=32'h80000000;
   endcase
  end
  if(t%8==7)begin valid_lanes[0]=1;scores[0+:32]=32'h7f800000;end
  start=1;@(negedge clk);start=0;
  if(t%6==2)begin
   // Abort at different points and restart with independently cleared state.
   repeat(5+t)@(negedge clk);rst_n=0;repeat(2)@(negedge clk);rst_n=1;
  end else begin
   wait(done[0]);repeat(3)@(negedge clk);
  end
 end
 $display("PASS lane writes lanes=%0d transactions=24 cycles=%0d",L,checked);$finish;
end
initial begin #10000000;$fatal(1,"timeout");end
endmodule
'''.replace('localparam L=LANES;', f'localparam L={lanes};'))
    sources = [ROOT/'rtl/ot_fp32_rne_pkg.sv', ROOT/'rtl/abi3/ot_a3_engine_pkg.sv',
               ROOT/'rtl/proto/ot_fp32_add_rne_pipe.sv',
               ROOT/'rtl/abi3/ot_a3_attention_softmax_block.sv', before, bench]
    if simulator == 'iverilog':
        command = ['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path/'sim'), *map(str,sources)]
        run = ['vvp', str(tmp_path/'sim')]
    else:
        executable = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
        command = [str(executable), '--binary', '--timing', '-j', '2', '-Wno-fatal',
                   '--top-module', 'tb', '--Mdir', str(tmp_path/'obj'), *map(str,sources)]
        run = [str(tmp_path/'obj/Vtb')]
    result = subprocess.run(command,capture_output=True,text=True,timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(run,capture_output=True,text=True,timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'PASS lane writes lanes={lanes} transactions=24' in result.stdout
