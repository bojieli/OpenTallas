module tb;reg clk=0;always #5 clk=~clk;reg rst=0,st=0;integer i,m=0,seen=0;reg[31:0] rng=32'h13579bdf;
wire [18:0] old0q;old0 u_old0(clk,rst,st,old0q);
wire [18:0] new0q;new0 u_new0(clk,rst,st,new0q);
wire [18:0] mut0q;mut0 u_mut0(clk,rst,st,mut0q);
wire [18:0] old1q;old1 u_old1(clk,rst,st,old1q);
wire [18:0] new1q;new1 u_new1(clk,rst,st,new1q);
wire [18:0] mut1q;mut1 u_mut1(clk,rst,st,mut1q);
initial begin repeat(20) @(negedge clk);for(i=0;i<12000;i=i+1) begin rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};rst=(i%107<13)?0:rng[4];st=rng[7];@(posedge clk);#1;
if(old0q !== new0q) m=m+1;if(old0q !== mut0q) seen=seen+1;
if(old1q !== new1q) m=m+1;if(old1q !== mut1q) seen=seen+1;
@ (negedge clk);end $display("RESET_LOCKSTEP cycles=%0d mismatches=%0d mutant_caught=%0d",i,m,seen);if(m!=0 || seen==0)$fatal(1,"reset lockstep failed");$finish;end endmodule
