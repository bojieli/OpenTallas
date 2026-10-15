`timescale 1ns/1ps
module tb_s81_hc_post_tile_static;
 reg clk=0;always #5 clk=~clk;reg rn=0,cv=0,hv=0,yv=0,rv=0,iv=0;
 reg[4:0]hr=0,yr=0,rr=0,ir=0;reg[255:0]hd=0;reg[127:0]yd=0,p=0;reg[511:0]c=0;
 wire ov,wv,ws,f;wire[255:0]od;wire[4:0]wr;integer cyc=0,got=0,writes=0,errors=0,first=-1,last=-1;
 ot_s81_hc_post_tile_static u(.clk(clk),.rst_n(rn),.coef_v(cv),.comb(c),.post(p),.h_v(hv),.h_slot(1'b0),.h_row(hr),.h_data(hd),
  .y_v(yv),.y_slot(1'b0),.y_row(yr),.y_data(yd),.compute_v(rv),.compute_slot(1'b0),.compute_row(rr),
  .inspect_v(iv),.inspect_slot(1'b0),.inspect_row(ir),.inspect_out_v(ov),.inspect_data(od),.writeback_v(wv),.writeback_row(wr),.writeback_slot(ws),.fault(f));
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)begin
  if(wv)begin writes++;if(first<0)first=cyc;last=cyc;end
  if(ov)begin got++;for(integer k=0;k<16;k=k+1)if(od[k*16+:16]!==16'h4000)errors++;end
 end
 initial begin
  repeat(3)@(negedge clk);rn=1;
  for(integer j=0;j<4;j=j+1)begin c[(4*j+j)*32+:32]=32'h3f800000;p[j*32+:32]=32'h3f800000;end
  if($test$plusargs("MUT_POST"))p[31:0]=0;
  cv=1;@(negedge clk);cv=0;
  for(integer row=0;row<20;row=row+1)begin
   hv=1;yv=1;hr=row;yr=row;hd={16{16'h3f80}};yd={4{32'h3f800000}};@(negedge clk);
  end
  hv=0;yv=0;repeat(4)@(negedge clk);
  for(integer row=0;row<20;row=row+1)begin rv=1;rr=row;@(negedge clk);end
  rv=0;repeat(32)@(negedge clk);
  for(integer row=0;row<20;row=row+1)begin iv=1;ir=row;@(negedge clk);end
  iv=0;repeat(5)@(negedge clk);
  $display("HC_POST_STATIC_TILE rows%0d writes%0d first%0d last%0d fault%0d errors%0d",got,writes,first,last,f,errors);
  if(got!=20||writes!=20||f||errors)$fatal(1,"HC_POST_STATIC_TILE FAIL");
  $display("HC_POST_STATIC_TILE PASS actual2SRAM actualRTL320BF16outputs");$finish;
 end
endmodule
