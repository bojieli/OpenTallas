`timescale 1ns/1ps
module tb_hgi_hc_weight_quarter_static;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;
 integer bank=0,quarter=0,wrong_id=0,n,s,r,q,l,checks=0;
 reg rst_n=0;reg[277:0]ap=0;reg rv=0,slot=0;reg[6:0]row=0;
 wire done,valid,fault;wire[255:0]data;
 ot_hgi_hc_weight_quarter_static #(.MUT_SLOT(MUT)) dut(.clk(clk),.rst_n(rst_n),.weight_ap(ap),
 .expected_bank_id(3'(bank^wrong_id)),.expected_quarter_id(2'(quarter)),.read_v(rv),.read_slot(slot),.read_row(row),
 .write_done(done),.read_valid(valid),.fault(fault),.weight_data(data));
 reg[255:0]golden[0:255],e[0:2];reg[2:0]v=0;reg enable=0;
 function automatic[31:0]pattern(input integer a,b);pattern=32'h3f000000^(a*32'h10103)^(b*32'h332211);endfunction
 always @(posedge clk)begin
  e[2]=e[1];e[1]=e[0];e[0]=golden[{slot,row}];v={v[1:0],rv&enable};#0.01;
  if(rst_n&&v[2])begin
   if(data!==e[2]||!valid)$fatal(1,"WEIGHT_QUARTER mismatch bank=%0d quarter=%0d check=%0d",bank,quarter,checks);
   checks=checks+1;
  end
 end
 initial begin
  if(!$value$plusargs("bank=%d",bank))bank=0;
  if(!$value$plusargs("quarter=%d",quarter))quarter=0;
  if(!$value$plusargs("wrong_id=%d",wrong_id))wrong_id=0;
  for(n=0;n<256;n=n+1)golden[n]=0;
  repeat(3)@(negedge clk);rst_n=1;
  for(s=0;s<2;s=s+1)for(r=0;r<128;r=r+1)for(q=0;q<4;q=q+1)begin
   ap=0;ap[277]=1;ap[276]=1'(s);ap[273+:3]=3'(bank);ap[266+:7]=7'(r);ap[264+:2]=2'(q);ap[7:0]=255;
   for(l=0;l<8;l=l+1)begin ap[8+l*32+:32]=pattern(s*512+r*4+q,l);if(q==quarter)golden[s*128+r][l*32+:32]=ap[8+l*32+:32];end
   @(negedge clk);
  end
  for(n=0;n<32;n=n+1)begin
   ap=0;ap[277]=1;ap[276]=1'(n);ap[273+:3]=3'(bank);ap[266+:7]=7'(n*3);ap[264+:2]=2'(quarter);ap[7:0]=8'h55;
   for(l=0;l<8;l=l+1)begin ap[8+l*32+:32]=pattern(9000+n,l);if(ap[l])golden[(n%2)*128+(n*3)%128][l*32+:32]=ap[8+l*32+:32];end
   @(negedge clk);
  end
  ap=0;repeat(3)@(negedge clk);
  for(n=0;n<8;n=n+1)begin rv=1;slot=1'(n);row=0;@(negedge clk);end
  enable=1;
  for(n=0;n<512;n=n+1)begin rv=1;slot=1'(n);row=7'(n/2);@(negedge clk);end
  enable=0;rv=0;repeat(4)@(negedge clk);
  if(fault||checks!=512)$fatal(1,"WEIGHT_QUARTER mismatch fault=%b checks=%0d",fault,checks);
  $display("WEIGHT_QUARTER PASS bank=%0d quarter=%0d checks=%0d macros=2 read_latency=3",bank,quarter,checks);$finish;
 end
endmodule
