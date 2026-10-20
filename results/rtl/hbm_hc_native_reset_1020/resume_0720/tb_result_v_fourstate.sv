`timescale 1ns/1ps
module tb_result_v_fourstate;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,launch=0;wire rv;integer cyc=0,launch_cyc=-1,results=0;
native_result_v_cone n(.clk(clk),.rst_n(rst_n),.launch(launch),.mixes(768'd0),.bases(768'd0),.scales(96'd0),.result_v(rv));
always @(posedge clk)begin
if(cyc<10 || launch || rv)$display("RV_4STATE_TRACE t=%0t cyc=%0d clk=%b reset=%b launch=%b valid=%b",$time,cyc,clk,rst_n,launch,rv);
if(!rst_n && rv!==1'b0)$fatal(1,"RV_4STATE_HELDLOW_FAIL");
if(launch)launch_cyc=cyc;
if(rv===1'b1)begin
 results=results+1;
 if(launch_cyc<0 || cyc-launch_cyc!=498)$fatal(1,"RV_4STATE_CALENDAR_FAIL delta=%0d",cyc-launch_cyc);
end
if(rv!==1'b0 && rv!==1'b1)$fatal(1,"RV_4STATE_UNKNOWN_VALID");
cyc=cyc+1;
end
initial begin
#0.1;$display("RV_4STATE_ASYNC t=%0t valid=%b",$time,rv);
if(rv!==0)$fatal(1,"RV_4STATE_STOPPED_CLOCK_ASSERT_FAIL");
repeat(5)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);launch=1;
@(negedge clk);launch=0;repeat(530)@(negedge clk);
if(results!=1)$fatal(1,"RV_4STATE_COUNT_FAIL count=%0d",results);
$display("RV_4STATE PASS heldlow_from_time0=1 stopped_clock_assert=1 requests=1 results=1 exact_latency=498");$finish;
end
endmodule
