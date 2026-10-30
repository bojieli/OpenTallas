`timescale 1ns/1ps
module status_tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;reg [143:0] bank_status=0;reg [2:0] hub_status=0;reg ring_fault=0;
wire [18:0] g,d,m;integer checks=0,bad=0,mut=0;
ot_vms_status_reference a(.*,.vmstat(g));
ot_vms_status_static #(.PRESERVE_STATUS_VALID(1)) b(.*,.vmstat(d));
ot_vms_status_mutant #(.PRESERVE_STATUS_VALID(1)) c(.*,.vmstat(m));
initial begin
repeat(2) @(negedge clk);
for(integer i=0;i<2000;i=i+1)begin
@(negedge clk);rst_n=(i%37!=0);bank_status={$random,$random,$random,$random,$random};hub_status=$random;ring_fault=$random;
@(posedge clk);#1;checks=checks+1;if(g!==d)bad=bad+1;if(g!==m)mut=mut+1;
end
$display("GLUE039_STATUS checks=%0d mismatches=%0d mutant=%0d",checks,bad,mut);
if(bad||!mut)$fatal(1,"status guard");$finish;
end endmodule
