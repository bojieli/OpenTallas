`timescale 1ns/1ps
module tb_sum;
reg [31:0] a,b,c,d; wire[31:0]y;reg[33:0]refsum;integer checks=0,overflows=0;reg[31:0]rng=32'h4285abcd;
ot_s81_ing_sum4_csa32 dut(.*);
function automatic[31:0]step(input[31:0]x);step=(x<<1)^{32{x[31]^x[21]^x[1]^x[0]}};endfunction
task automatic check;begin #1;refsum={2'b0,a}+{2'b0,b}+{2'b0,c}+{2'b0,d};checks=checks+1;if(refsum[33:32]!=0)overflows=overflows+1;if(y!==refsum[31:0])$fatal(1,"sum mismatch %h %h %h %h actual%h ref%h",a,b,c,d,y,refsum);end endtask
initial begin
 a=0;b=0;c=0;d=0;check();a='1;b='1;c='1;d='1;check();
 for(integer i=0;i<32;i=i+1)begin a=32'b1<<i;b=a;c=a;d=a;check();a=(32'b1<<i)-1;b=1;c=0;d=0;check();a='1;b=1;c='1;d=1;check();end
 for(integer i=0;i<1000000;i=i+1)begin rng=step(rng);a=rng;rng=step(rng);b=rng;rng=step(rng);c=rng;rng=step(rng);d=rng;check();end
 $display("SUM4_CSA32 PASS checks=%0d overflows=%0d bits=32 latency=0",checks,overflows);$finish;
end
endmodule
