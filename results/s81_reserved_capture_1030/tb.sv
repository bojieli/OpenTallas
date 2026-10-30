`timescale 1ns/1ps
module tb;
 reg clk=0; always #5 clk=~clk;
 reg [597:0] din=0;
 wire [594:0] old_body={din[597],din[593:0]};
 wire [594:0] new_body={din[597],din[593:0]};
 wire [594:0] bad_body={din[597],din[593:1],~din[0]};
 ot_dp_reserved_capture dut(clk,din[596:594]);
 ot_dp_reserved_capture mutant(clk,{din[594],din[595],din[596]});
 integer n,checks=0, bad_capture=0,bad_body_count=0;
 reg[2:0] expected;
 initial begin
 for(n=0;n<1024;n=n+1)begin
 @(negedge clk); din={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random}; expected=din[596:594];
 @(posedge clk); #1;
 if(old_body !== new_body || dut.q !== expected) $fatal(1,"miter/capture fail");
 checks=checks+1;
 if(mutant.q !== expected)bad_capture=bad_capture+1;
 if(bad_body !== old_body)bad_body_count=bad_body_count+1;
 end
 if(bad_capture==0 || bad_body_count==0)$fatal(1,"mutant did not fail");
 $display("PASS checks=%0d capture_mutant=%0d functional_mutant=%0d added_observable_cycles=0",checks,bad_capture,bad_body_count);$finish;
 end
endmodule
