`timescale 1ns/1ps
module tb_s81_hc_rows_static;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,wv=0,ws=0,rv=0,rs=0,bv=0,bs=0;
 reg [4:0] wi=0,ri=0;reg[31:0]wt=0,rt=0,bt=0;
 reg[8191:0]wd=0;wire ov,os,f;wire[8191:0]od;wire[31:0]ot;wire[4:0]oi;
 integer cyc=0,got=0,errors=0,first=-1;
 ot_s81_hc_rows_static u(.clk(clk),.rst_n(rn),.wr_v(wv),.wr_slot(ws),.wr_row(wi),.wr_tag(wt),.wr_data(wd),
  .reserve_v(bv),.reserve_slot(bs),.reserve_tag(bt),.rd_v(rv),.rd_slot(rs),.rd_row(ri),.rd_tag(rt),
  .out_v(ov),.out_data(od),.out_tag(ot),.out_row(oi),.out_slot(os),.fault(f));
 function automatic [8191:0] payload(input integer slot,row);
  reg[8191:0]x;
  begin for(integer l=0;l<256;l=l+1)x[l*32+:32]=32'h3f800000^(slot<<24)^(row<<12)^l;return x;end
 endfunction
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)if(rn&&ov)begin
  if(first<0)first=cyc;
  if(od!==payload(os,oi)||ot!==(32'h12340000+os))errors++;
  got++;
 end
 initial begin
  repeat(3)@(negedge clk);rn=1;
  for(integer s=0;s<2;s=s+1)begin
   bv=1;bs=s;bt=32'h12340000+s;@(negedge clk);bv=0;
   repeat(2)@(negedge clk);
   for(integer r=0;r<20;r=r+1)begin
    wv=1;ws=s;wi=r;wt=32'h12340000+s;wd=payload(s,r);
    if($test$plusargs("MUT_TAG")&&s==1&&r==7)wt=wt^1;
    @(negedge clk);
   end
   wv=0;
  end
  repeat(4)@(negedge clk);
  for(integer s=0;s<2;s=s+1)for(integer r=0;r<20;r=r+1)begin
   rv=1;rs=s;ri=r;rt=32'h12340000+s;@(negedge clk);
  end
  rv=0;repeat(5)@(negedge clk);
  if(errors||f||got!=40)$fatal(1,"HC_STATIC_ROWS FAIL got%0d errors%0d fault%0d first%0d",got,errors,f,first);
  $display("HC_STATIC_ROWS PASS actual32SRAM 40rows10240FP32words first%0d done%0d",first,cyc);$finish;
 end
endmodule
