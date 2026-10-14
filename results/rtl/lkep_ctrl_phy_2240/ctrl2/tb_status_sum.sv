module tb_lkep_status_sum_2240;
 reg clk=0,rst_n=0;
 ot_lkep_ctrl_phy dut(.clk(clk),.rst_n(rst_n));
 reg [31:0] a,b,c,sx,sy,want,got,rng;
 integer i;
 function automatic [31:0] rnd(input [31:0] x);
 reg[31:0] q;begin q=x^(x<<13);q=q^(q>>17);rnd=q^(q<<5);end endfunction
 initial begin
 rng=32'h8a315271;
 for(i=0;i<1000000;i=i+1) begin
 rng=rnd(rng);a=rng;rng=rnd(rng);b=rng;rng=rnd(rng);c=rng;
 if(i<32) begin a=(32'h1<<i)-1;b=32'hffffffff;c=32'h1<<i;end
 sx=a^b^c;sy=((a&b)|(a&c)|(b&c))<<1;want=a+b+c;got=dut.add32_prefix(sx,sy);
 if(got!==want)$fatal(1,"STATUS_SUM FAIL vector=%0d got=%x want=%x",i,got,want);
 end
 $display("STATUS_SUM PASS vectors=%0d includes unsigned wrap and carry boundaries",i);$finish;
 end
endmodule
