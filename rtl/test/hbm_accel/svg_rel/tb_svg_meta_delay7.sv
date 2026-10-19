`timescale 1ns/1ps
module tb_svg_meta_delay7;
 parameter MUT=0;reg clk=0;always #5 clk=~clk;
 reg rst=0;reg[34:0]d=0;wire[34:0]q;
 reg[34:0]gold[0:6];integer i,n,round,errors=0,checks=0;
 ot_hbm_svg_meta_delay7 #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst),.data_in(d),.data_out(q));
 always @(posedge clk)begin
  if(!rst)for(i=0;i<7;i=i+1)gold[i]=0;
  else begin for(i=6;i>0;i=i-1)gold[i]=gold[i-1];gold[0]=d;end
  #1;if(q!==gold[6])begin errors=errors+1;if(errors<4)$display("META_FAIL q=%h gold=%h",q,gold[6]);end
  checks=checks+1;
 end
 initial begin
  for(round=0;round<3;round=round+1)begin
   rst=0;repeat(3)@(negedge clk);rst=1;
   for(n=0;n<257;n=n+1)begin d={3'(round),16'(n),16'(n^16'hd031)};@(negedge clk);end
  end
  rst=0;repeat(2)@(negedge clk);
  if(errors)begin $display("META_FAIL mut=%0d errors=%0d",MUT,errors);$fatal(1);end
  $display("META_PASS checks=%0d",checks);$finish;
 end
endmodule
