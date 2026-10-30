module tb;reg clk=0;always #5 clk=~clk;reg rst=0,st=0;integer i,m=0,seen=0;reg[31:0] rng=32'h13579bdf;
wire[16:0] dut0q;dut0 udut0(clk,rst,st,dut0q);
wire[16:0] mut0q;mut0 umut0(clk,rst,st,mut0q);
wire[16:0] dut1q;dut1 udut1(clk,rst,st,dut1q);
wire[16:0] mut1q;mut1 umut1(clk,rst,st,mut1q);
initial begin repeat(20)@(negedge clk);for(i=0;i<12000;i=i+1)begin rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};rst=(i%107<13)?0:rng[4];st=rng[7];@(posedge clk);#1;
if(dut0q !== {17{dut0q[0]}})m=m+1;if(dut0q!==mut0q)seen=seen+1;
if(dut1q !== {17{dut1q[0]}})m=m+1;if(dut1q!==mut1q)seen=seen+1;
@(negedge clk);end $display("R6W7_RAW_EQUAL cycles=%0d mismatches=%0d mutant=%0d",i,m,seen);if(m||!seen)$fatal(1,"raw copy epoch mismatch");$finish;end endmodule