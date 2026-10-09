`timescale 1ps/1fs
module tb_sum96_final_tree;
 reg clk=0;always #416.6665 clk=~clk;
 reg rst_n=0,v=0;
 reg [6143:0] d;
 wire ov,fault;wire [511:0] y;
 reg [6143:0] partial[0:63];reg [511:0] expected[0:63];
 integer sent=0,got=0,cycles=0;
 ot_hgi_sum96_final_tree dut(.clk(clk),.rst_n(rst_n),.valid_in(v),.partials(d),.valid_out(ov),.data_out(y),.fault(fault));
 always @(posedge clk) if(rst_n)begin
 cycles<=cycles+1;
 if(fault)$fatal(1,"unexpected arithmetic fault");
 if(ov)begin
 if(y!==expected[got])$fatal(1,"SUM mismatchwordtile%0d got%h expected%h",got,y,expected[got]);
 got<=got+1;
 if(got==63)begin $display("PASS real96x256:4cases,64tiles,1024FP32words,cycle%0d",cycles);$finish;end
 end
 if(cycles>400)$fatal(1,"completion timeout");
 end
 initial begin
 $readmemh("partials.hex",partial);$readmemh("expected.hex",expected);
 repeat(4)@(negedge clk);rst_n=1;
 for(sent=0;sent<64;sent=sent+1)begin
 @(negedge clk);v=1;d=partial[sent];
`ifdef MUTANT_TREE
 // Shift subgroup rankorder byone: changedpairtree consumes actualinputs.
 d={partial[sent][511:0],partial[sent][6143:512]};
`endif
`ifdef MUTANT_DROP
 d[11*512+:512]=512'd0;
`endif
 if(sent%3==2)begin @(negedge clk);v=0;end
 end
 @(negedge clk);v=0;
 end
endmodule
