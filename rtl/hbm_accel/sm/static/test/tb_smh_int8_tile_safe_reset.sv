`timescale 1ns/1ps
module tb_smh_int8_tile_safe_reset;
reg clk=0, run=1, rst_n=0, iv=0;
always #1 if(run) clk=~clk;
reg a,b;
always @(posedge clk) begin a<=rst_n; b<=a; end
wire v0,v1; wire[9:0]t0,t1;wire[1023:0]d0,d1;wire[34:0]s0,s1;
ot_smh_int8_tile base(clk,b,iv,10'd17,{128{8'h81}},v0,t0,d0,s0);
ot_smh_int8_tile_safe dut(clk,rst_n,iv,10'd17,{128{8'h81}},v1,t1,d1,s1);
integer checks=0,phase,p,j;
reg armed=0;
always @(negedge clk) if(armed) begin
 checks=checks+1;
 if({v0,t0,s0} !== {v1,t1,s1} || (v0 && d0!==d1)) $fatal(1,"RESET LOCKSTEP FAIL %0t",$time);
 if(dut.reset_final !== {9{b}}) $fatal(1,"RESET STAGE FAIL %0t",$time);
end
initial begin
 repeat(5) @(negedge clk); armed=1;
 // phases include pulses too short to sample, captured assertion/release,
 // and stopped-clock assertion/release: no asynchronous wrapper assertion.
 for(phase=0;phase<16;phase=phase+1) begin
   @(negedge clk); rst_n=1; repeat(5) @(negedge clk);
   iv=1; @(negedge clk); iv=0; repeat(4) @(negedge clk);
   #(0.02+phase*0.05) rst_n=0;
   #0.3 rst_n=1;
   repeat(4) @(negedge clk);
   #(0.02+phase*0.05) rst_n=0;
   repeat(3) @(negedge clk); #0.1 rst_n=1;
   repeat(5) @(negedge clk);
   run=0; #0.2 rst_n=0; #3;
   if(dut.reset_final !== {9{b}}) $fatal(1,"STOPPED ASSERT CHANGED");
   rst_n=1; #3;
   if(dut.reset_final !== {9{b}}) $fatal(1,"STOPPED RELEASE CHANGED");
   run=1; repeat(5) @(negedge clk);
 end
 $display("I8T RESET PASS checks=%0d phases=16 stopped=16",checks);$finish;
end
endmodule
