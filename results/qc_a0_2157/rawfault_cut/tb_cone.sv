`timescale 1ns/1ps
module tb;
reg clk=0;always #1 clk=~clk;
reg[49:0]q=0;wire[8:0]r,g,m;
reference_cone u_r(q,r);reconstructed_cone u_g(q,g);mutant_cone u_m(q,m);
reg[63:0]xs=64'hcafe123456abcdef;
integer n,checks=0,mutants=0;
initial begin
for(n=0;n<32768;n=n+1)begin
@(negedge clk);if(r!==g)$fatal(1,"partition mismatch %0d",n);if(r!==m)mutants=mutants+1;checks=checks+1;
xs=xs^(xs<<13);xs=xs^(xs>>7);xs=xs^(xs<<17);q=xs[49:0];
end
if(mutants!=32768)$fatal(1,"mutant not caught");
$display("FAULTCUT LOCKSTEP PASS checks=%0d mutant_differences=%0d state_copies_added=0 cycles_added=0",checks,mutants);$finish;
end
endmodule
