"""Exercise exact-result cache lifetime with a fault-controllable service."""
from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('lanes',[1,2])
@pytest.mark.parametrize('source',['rtl/abi3/ot_a3_attention_softmax_block.sv','results/rtl/softmax_cache2/candidate.sv'])
@pytest.mark.parametrize('simulator',['iverilog','verilator'])
def test_failed_results_and_reset(tmp_path,simulator,source,lanes):
    bench=tmp_path/'tb.sv'
    bench.write_text(r'''module ot_a3_fp32_transcendental_cr_rne #(parameter ENABLE_SIGMOID=1)(
input clk,rst_n,in_valid,operation,out_ready,input [31:0] argument_code,
output in_ready,output reg out_valid,output reg [31:0] result_code,output reg [1:0] result_error);
assign in_ready=!out_valid;
always @(posedge clk)begin
 if(!rst_n)begin out_valid<=0;result_code<=0;result_error<=0;end
 else begin
  if(out_valid && out_ready)out_valid<=0;
  if(in_valid && in_ready)begin
   out_valid<=1;result_error<=tb.fail_service?2'd1:2'd0;
   result_code<=tb.fail_service?32'hdeadbeef:(argument_code==32'hbf800000 ? 32'h3f000000 : (argument_code==32'hc0000000 ? 32'h3e800000 : 32'h3f800000));
   if(argument_code[30:0]!=0 && argument_code!=32'hbf800000 && argument_code!=32'hc0000000)$fatal(1,"unexpected offset");
  end
 end
end
endmodule
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0,fail_service=0;wire busy,done;wire [31:0] updated_max,rescale,exp_count;wire [LANE_COUNT*32-1:0] probabilities;
reg [LANE_COUNT*32-1:0] scores=LANE_SCORES;wire [7:0] error_code;
integer requests=0,before_requests;
ot_a3_attention_softmax_block #(.LANES(LANE_COUNT)) dut(.clk(clk),.rst_n(rst_n),.start(start),.cfg_first(1'b1),.cfg_running_max(32'd0),.lane_valid({LANE_COUNT{1'b1}}),.scores(scores),.busy(busy),.done(done),.updated_max(updated_max),.rescale(rescale),.probabilities(probabilities),.error_code(error_code),.exp_count(exp_count));
always @(posedge clk)if(rst_n && dut.exp_in_valid && dut.exp_in_ready)requests<=requests+1;
task run_case(input fail,input integer expected_requests);begin
 before_requests=requests;fail_service=fail;start=1;@(negedge clk);start=0;
 wait(done);@(negedge clk);
 if(requests-before_requests!=expected_requests)$fatal(1,"wrong cache service count");
 if(fail && error_code==0)$fatal(1,"failure hidden");
 if(!fail && (error_code!=0 || probabilities[31:0]!=32'h3f800000 || exp_count!=LANE_COUNT))$fatal(1,"wrong cached result");
 if(!fail && LANE_COUNT==2 && probabilities[63:32] !==
    (scores[63:32]==32'hbf800000 ? 32'h3f000000 : 32'h3e800000))
  $fatal(1,"second cache entry selected wrong result");
 repeat(2)@(negedge clk);
end endtask
initial begin
 repeat(2)@(negedge clk);rst_n=1;
 run_case(1,1);run_case(1,1); // repeated errors must never populate the cache
 run_case(0,LANE_COUNT);run_case(0,REPEAT_REQUESTS); // successful result reused across block starts
 rst_n=0;@(negedge clk);rst_n=1;
 run_case(0,LANE_COUNT); // reset invalidates payload without requiring its reset
 if(LANE_COUNT==2)begin
  scores[63:32]=32'hc0000000;
  run_case(1,FAIL_REQUESTS);run_case(1,1);
  run_case(0,RETRY_REQUESTS);run_case(0,POST_RETRY_REQUESTS);run_case(0,REPEAT_REQUESTS);
 end
 $display("PASS cache failure exclusion and reset");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
'''.replace('LANE_COUNT',str(lanes)).replace('LANE_SCORES',"64'hbf80000000000000" if lanes==2 else "32'd0").replace('REPEAT_REQUESTS',str(0 if 'cache2' in source or lanes==1 else 2)).replace('FAIL_REQUESTS',str(1)).replace('POST_RETRY_REQUESTS',str(1 if 'cache2' in source else 2)).replace('RETRY_REQUESTS',str(1 if 'cache2' in source else 2)))
    sources=[str(ROOT/'rtl/ot_fp32_rne_pkg.sv'),str(ROOT/'rtl/abi3/ot_a3_engine_pkg.sv'),str(ROOT/'rtl/proto/ot_fp32_add_rne_pipe.sv'),str(ROOT/source),str(bench)]
    if simulator=='iverilog':
        cmd=['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),*sources];run=['vvp',str(tmp_path/'sim')]
    else:
        cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-j','4','-Wno-fatal','--top-module','tb','--Mdir',str(tmp_path/'obj'),*sources];run=[str(tmp_path/'obj/Vtb')]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);assert r.returncode==0,r.stdout+r.stderr
    r=subprocess.run(run,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stdout+r.stderr
    assert 'PASS cache failure' in r.stdout
