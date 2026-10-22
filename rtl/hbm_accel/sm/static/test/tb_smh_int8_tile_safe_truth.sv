`timescale 1ns/1ps
module tb_smh_int8_tile_safe_truth;
reg clk=0, run=1, rst_n=0, iv=0;
always #1 if(run) clk=~clk;
reg a,b; reg[1023:0]codes=0; integer code,lane;
always @(posedge clk) begin a<=rst_n; b<=a; end
wire v0,v1; wire[9:0]t0,t1;wire[1023:0]d0,d1;wire[34:0]s0,s1;
ot_smh_int8_tile base(clk,b,iv,10'd17,codes,v0,t0,d0,s0);
ot_smh_int8_tile_safe dut(clk,rst_n,iv,10'd17,codes,v1,t1,d1,s1);
integer checks=0,phase,p,j;
reg armed=0;
always @(negedge clk) if(armed) begin
 checks=checks+1;
 if({v0,t0,s0} !== {v1,t1,s1} || (v0 && d0!==d1)) $fatal(1,"RESET LOCKSTEP FAIL %0t",$time);
 if(dut.reset_final !== {9{b}}) $fatal(1,"RESET STAGE FAIL %0t",$time);
end
initial begin
 repeat(5) @(negedge clk); armed=1;
 rst_n=1; repeat(5) @(negedge clk);
 for(code=0;code<256;code=code+1) begin
   for(lane=0;lane<128;lane=lane+1) codes[8*lane+:8]=(code+lane)%256;
   iv=1; @(negedge clk); iv=0; repeat(3) @(negedge clk);
 end
 repeat(5) @(negedge clk);
 $display("I8T TRUTH PASS checks=%0d codes=256 lanes=128",checks);$finish;
end
endmodule
