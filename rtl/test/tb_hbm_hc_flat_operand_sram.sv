`timescale 1ns/1ps
module tb_hbm_hc_flat_operand_sram(input wire clk);
 reg rst_n=0,start=0,iv=0;wire ir,ready,fault;
 reg[15:0]lease=16'h3210;reg[10:0]beat=0;reg[255:0]data=0;
 reg[7:0]re=0;reg[127:0]addr=0;wire[4095:0]q;wire[127:0]ce,ue;
 integer cyc=0,sent=0,readstart=0,readword=0,checks=0,ces=0,ues=0,mode=0,b,l;
 reg injected=0,poison_seen=0;
 function automatic[15:0]value(input integer i);value=16'(i*1237)^16'h9163;endfunction
 ot_hbm_hc_flat_operand_sram dut(.clk(clk),.rst_n(rst_n),.start(start),.release_window(1'b0),.lease(16'h3210),
  .i_valid(iv),.i_ready(ir),.i_lease(lease),.i_beat(beat),.i_data(data),.ready(ready),
  .re(re),.addr(addr),.q(q),.fault(fault),.ce_seen(ce),.ue_seen(ue));
 initial begin
  if($test$plusargs("CE"))mode=1;if($test$plusargs("CHECK"))mode=2;
  if($test$plusargs("UE"))mode=3;if($test$plusargs("BADLEASE"))mode=4;
  if($test$plusargs("DUP"))mode=5;
 end
 always @(posedge clk)begin
  cyc<=cyc+1;if(cyc==4)rst_n<=1;start<=cyc==7;iv<=0;re<=0;
  if(ir&&sent<1280&&cyc%7!=0)begin
   iv<=1;beat<=11'(sent);lease<=mode==4?16'h3211:16'h3210;
   for(l=0;l<16;l=l+1)data[l*16+:16]<=value(sent*16+l);
   if(mode==5&&sent==1)beat<=0;
   sent=sent+1;
  end
  if(ready&&!injected)begin
   injected=1;readstart=cyc+2;
   if(mode==1)dut.bank[3].ram[0].sram.mem[13][255]=~dut.bank[3].ram[0].sram.mem[13][255];
   if(mode==2)dut.bank[3].ram[1].sram.mem[13][10]=~dut.bank[3].ram[1].sram.mem[13][10];
   if(mode==3)dut.bank[3].ram[0].sram.mem[13][255:254]=dut.bank[3].ram[0].sram.mem[13][255:254]^2'b11;
  end
  if(injected&&cyc>=readstart&&readword<80&&(cyc-readstart)%5==0)begin
   re<=8'hff;for(b=0;b<8;b=b+1)addr[b*16+:16]<=16'(readword);readword=readword+1;
  end
  if(|ce)ces=ces+1;
  if(|ue)begin ues=ues+1;if(q[(3*16+6)*32+:32]===0)poison_seen=1;end
  if(fault)begin
   if(mode==3&&ues>0&&poison_seen)begin $display("HC_FLAT_PASS UE_POISON");$finish;end
   if(mode==4||mode==5)begin $display("HC_FLAT_PASS protocol_reject mode=%0d",mode);$finish;end
   $fatal(1,"unexpectedflatfault mode%0d",mode);
  end
  if(mode!=3&&injected&&cyc>=readstart+4&&(cyc-readstart)%5==4&&checks<80)begin
   for(b=0;b<8;b=b+1)for(l=0;l<32;l=l+1)
    if(q[(b*32+l)*16+:16]!==value(8*(checks*32+l)+b))$fatal(1,"flat mismatch word%0d bank%0d lane%0d",checks,b,l);
   checks=checks+1;
   if(checks==80)begin
    if(mode!=0&&ces!=1)$fatal(1,"flat CE count%0d",ces);
    $display("HC_FLAT_PASS mode=%0d words=80 exactbits=327680 ce=%0d",mode,ces);$finish;
   end
  end
  if(cyc>10000)$fatal(1,"flat protocoltimeout");
 end
endmodule
