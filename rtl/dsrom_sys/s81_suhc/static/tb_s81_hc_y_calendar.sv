`timescale 1ns/1ps
module tb_s81_hc_y_calendar;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,start=0,slot=0,pv=0;reg[31:0]tag=32'h12345678,pt=32'h12345678;reg[8191:0]pd=0;
 wire ov,os,done,f;wire[8191:0]od;wire[31:0]ot;wire[4:0]oi;
 integer cyc=0,t0,first=-1,last=-1,doneat=-1,got=0,errors=0;
 ot_s81_hc_y_calendar u(.clk(clk),.rst_n(rn),.start(start),.slot(slot),.job_tag(tag),.producer_v(pv),
 .producer_tag(pt),.producer_data(pd),.out_v(ov),.out_data(od),.out_tag(ot),.out_row(oi),.out_slot(os),.done(done),.fault(f));
 function automatic [8191:0]data(input integer row);
  reg[8191:0]x;begin for(integer l=0;l<256;l=l+1)x[l*32+:32]=32'h3f800000^(row<<12)^l;return x;end
 endfunction
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)begin
  if(ov)begin got++;if(first<0)first=cyc-t0;last=cyc-t0;if(od!==data(oi)||ot!==tag||os!=slot)errors++;end
  if(done)doneat=cyc-t0;
 end
 initial begin
  repeat(3)@(negedge clk);rn=1;repeat(3)@(negedge clk);
  start=1;t0=cyc;@(negedge clk);start=0;
  repeat(4)@(negedge clk);
  for(integer row=0;row<20;row=row+1)begin
   pv=1;pt=tag;pd=data(row);
   if($test$plusargs("MUT_MISSING")&&row==7)pv=0;
   @(negedge clk);
  end
  pv=0;repeat(16)@(negedge clk);
  $display("HC_Y_CALENDAR calendar got%0d first%0d last%0d done%0d fault%0d errors%0d",got,first,last,doneat,f,errors);
  if(got!=20||errors||f||doneat<0)$fatal(1,"HC_Y_CALENDAR FAIL");
  $display("HC_Y_CALENDAR PASS actual32SRAM 5120FP32words fixedwrite/read");$finish;
 end
endmodule
