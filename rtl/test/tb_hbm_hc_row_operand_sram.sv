`timescale 1ns/1ps
module tb_hbm_hc_row_operand_sram(input wire clk);
 reg rst_n=0,start=0;wire ready,qv,rr,fault;wire[29:0]qa;wire[2:0]ql;wire[9:0]qt;
 reg rv=0;reg[9:0]rt=0;reg[1:0]rb=0;reg[255:0]rd=0;
 reg[7:0]re=0;reg[127:0]ra=0;wire[8191:0]q;wire[31:0]ce,ue;
 integer cyc=0,left=0,beat=0,word=0,base=0,readword=0,readstart=0,checks=0,ces=0,ues=0;
 integer mode=0,b,s,l;reg injected=0,poison_seen=0;reg[9:0]tag;
 wire qr=(left==0);
 function automatic[31:0]pattern(input integer bank,wordidx,lane);
  pattern=32'hac350001 ^ (bank*32'h1365f2b7) ^ (wordidx*32'h73c29135) ^ (lane*32'h13579765);
 endfunction
 ot_hbm_hc_row_operand_sram dut(.clk(clk),.rst_n(rst_n),.start(start),.release_window(1'b0),
  .hbm_base(30'd0),.ready(ready),.hq_v(qv),.hq_rdy(qr),.hq_addr(qa),.hq_len(ql),.hq_tag(qt),
  .hr_v(rv),.hr_rdy(rr),.hr_tag(rt),.hr_beat(rb),.hr_data(rd),.rom_re(re),.rom_addr(ra),.rom_q(q),
  .fault(fault),.ce_seen(ce),.ue_seen(ue));
 initial begin
  if($test$plusargs("CE"))mode=1;
  if($test$plusargs("CHECK"))mode=2;
  if($test$plusargs("UE"))mode=3;
  if($test$plusargs("DUP"))mode=4;
 end
 always @(posedge clk) begin
  cyc<=cyc+1;if(cyc==4)rst_n<=1;start<=cyc==7;rv<=0;re<=0;
  if(qv&&qr)begin tag=qt;left=ql;beat=0;end
  else if(left>0)begin
   rv<=1;rt<=tag;rb<=2'(beat);
   for(l=0;l<8;l=l+1)rd[l*32+:32]<=pattern(int'(tag[9:7]),int'(tag[6:0]),beat*8+l);
   beat=beat+1;left=left-1;
   if(mode==4 && tag==0 && beat==2)begin rb<=0;end
  end
  if(ready&&!injected)begin
   injected=1;readstart=cyc+2;
   if(mode==1)dut.bank[0].sector[0].ram.mem[0][0]=~dut.bank[0].sector[0].ram.mem[0][0];
   if(mode==2)dut.bank[0].ck.mem[0][0]=~dut.bank[0].ck.mem[0][0];
   if(mode==3)dut.bank[0].sector[0].ram.mem[0][1:0]=dut.bank[0].sector[0].ram.mem[0][1:0]^2'b11;
  end
  if(injected && cyc>=readstart && readword<80 && (cyc-readstart)%5==0)begin
   re<=8'hff;for(b=0;b<8;b=b+1)ra[b*16+:16]<=16'(readword);
   word=readword;readword=readword+1;
  end
  if(|ce)ces=ces+1;if(|ue)begin ues=ues+1;if(q[255:0]===256'd0)poison_seen=1;end
  if(mode==4 && fault)begin $display("HC_SRAM_PASS mode=DUP rejected=1");$finish;end
  if(mode==3 && fault)begin
   if(ues==0 || !poison_seen)$fatal(1,"UE not poisoned");
   $display("HC_SRAM_PASS mode=UE rejected=1 poisoned=1");$finish;
  end
  if(fault && mode!=3 && mode!=4)$fatal(1,"unexpected SRAM fault");
  // Re assigned after issue edge, SRAM captures next edge, decoder2 follows.
  if(mode!=3 && injected && cyc>=readstart+4 && (cyc-readstart)%5==4 && checks<80)begin
   for(b=0;b<8;b=b+1)for(s=0;s<4;s=s+1)for(l=0;l<8;l=l+1)
    if(q[(b*4+s)*256+l*32+:32]!==pattern(b,checks,s*8+l))$fatal(1,"data mismatch row%0d bank%0d sector%0d",checks,b,s);
   checks=checks+1;
   if(checks==80)begin
    if(mode!=0 && ces!=1)$fatal(1,"single error not corrected count%0d",ces);
    $display("HC_SRAM_PASS mode=%0d words=%0d exactbits=%0d ce=%0d ue=%0d",mode,checks,checks*8192,ces,ues);$finish;
   end
  end
  if(cyc>10000)$fatal(1,"SRAM gate timeout");
 end
endmodule
