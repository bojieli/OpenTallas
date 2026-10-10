`timescale 1ns/1ps
module tb;
reg ck=0; always #1 ck=~ck;
reg [514:0] q=0; wire [2059:0] qa,qb,qc;
dsfd_svcio_q_original a(.ck(ck),.rst(1'b1),.q(q),.q_q(qa));
dsfd_svcio_q #(.OSTG(0)) b(.ck(ck),.rst(1'b1),.q(q),.q_q(qb));
dsfd_svcio_q #(.OSTG(1)) c(.ck(ck),.rst(1'b1),.q(q),.q_q(qc));
reg [514:0] hist[0:2047]; integer i,j; integer seed=32'h6fbc9271;
initial begin
for(i=0;i<1536;i=i+1) begin
 @(negedge ck);
 if(i<515) q=515'b1 << i;
 else for(j=0;j<515;j=j+1) q[j]=$random(seed);
 hist[i]=q;
 if(i>=4) begin
 if(qa!=={4{hist[i-3]}} || qb!==qa || qc!=={4{hist[i-4]}}) $fatal(1,"q mismatch at %0d",i);
 end
end
$display("PASS q source equivalence 1536 full-width words; legacy=current OSTG0 3 cycles, OSTG1 4 cycles");$finish;
end
endmodule
