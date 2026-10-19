`timescale 1ns/1ps
module tb_s81_bundle_token_return;
 reg clk=0,rst_n=0,go=0; always #0.5 clk=~clk;
 reg[46:0] owner=0;reg[63:0] seq=0;
 reg[255:0] xa=0,xb=0;reg[16:0] row0=21888;
 wire[3:0] hv;wire[127:0] hd;wire[67:0] hr;
 wire tv,fault;wire[31:0] ti,tb;wire[46:0] towner;wire[63:0] ts;
 ot_s81_bundle_token_return dut(clk,rst_n,go,owner,seq,row0,xa,xb,hv,hd,hr,tv,ti,tb,towner,ts,fault);
 reg[255:0] ma[0:255],mb[0:63];reg[31:0] expect_logits[0:127];reg[31:0] ex[0:1];
 string dir;integer mode=0,mut=0,deadline=-1,cyc=0,g0=0,n=0,bad=0,got=0,cases=0,c,k,age,seen;
 reg delayed_tv=0;reg[31:0] delayed_ti,delayed_tb;reg[46:0] delayed_owner;reg[63:0] delayed_seq;
 always@(posedge clk)begin cyc<=cyc+1;delayed_tv<=tv;delayed_ti<=ti;delayed_tb<=tb;delayed_owner<=towner;delayed_seq<=ts;end
 wire obs_v=(mut==3)?delayed_tv:tv;
 wire[31:0] obs_id=(mut==3)?delayed_ti:ti,obs_bits=(mut==3)?delayed_tb:tb;
 wire[46:0] obs_owner=((mut==3)?delayed_owner:towner)^((mut==2)?47'd1:47'd0);
 wire[63:0] obs_seq=(mut==3)?delayed_seq:ts;
 always@(negedge clk)if(rst_n)begin
  for(integer q=0;q<4;q=q+1)if(hv[q])begin
   n=n+1;
   if(hr[17*q+:17]<row0||hr[17*q+:17]>=row0+128||hd[32*q+:32]!==expect_logits[hr[17*q+:17]-row0])bad=bad+1;
  end
  if(obs_v)begin
   age=cyc-g0;seen=seen+1;got=got+1;
   $display("RETURN case=%0d owner=%h seq=%h row=%0d bits=%h age=%0d",cases,obs_owner,obs_seq,obs_id,obs_bits,age);
   if(obs_id!==ex[0]||obs_bits!==ex[1]||obs_owner!==owner||obs_seq!==seq||seen!=1||(deadline>=0&&age!=deadline))bad=bad+1;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  if($value$plusargs("MODE=%d",mode))begin end
  if($value$plusargs("MUT=%d",mut))begin end
  if($value$plusargs("DEADLINE=%d",deadline))begin end
  if(mut==1)force dut.u_field.head_d=128'd0;
  $readmemh({dir,"/xa.hex"},ma);$readmemh({dir,"/xb.hex"},mb);
  $readmemh({dir,"/logits.hex"},expect_logits);$readmemh({dir,"/expect.hex"},ex);
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
  for(k=0;k<(mode?3:1);k=k+1)begin
   owner=47'h12345670000+k;seq=64'h123456789abc0000+64'(k*256);seen=0;n=0;
   @(negedge clk);g0=cyc;go=1;
   for(c=1;c<9000;c=c+1)begin
    @(negedge clk);go=0;
    if(c>=5&&c<8300)begin xa=ma[(c-5)%256];xb=mb[(c-5)%64];end
   end
   if(seen!=1||n!=128||fault)bad=bad+1;
   cases=cases+1;
  end
  $display("LIVE_HEAD_RETURN %s mode=%0d mut=%0d cases=%0d returns=%0d bad=%0d fault=%0d",bad==0?"PASS":"FAIL",mode,mut,cases,got,bad,fault);
  $finish;
 end
endmodule
