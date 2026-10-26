`timescale 1ns/1ps
module tb_tkx_pinreg;
 parameter integer LINK_STAGES=2;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,boot_start=0;reg[2340:0]raw=0;
 wire[1170:0]nb,pb;wire ntf,ptf,ns,ps,nrf,prf;wire[2340:0]nq,pq;
 ot_hbm_tkx_2beat_tx nt(clk,rst_n,boot_start,raw,nb,ntf,ns);
 wire[2340:0]pr_raw=raw|((check&&$test$plusargs("MUT_PHASE")&&!ps)?{8'd0,1'b1,{2332{1'b0}}}:2341'd0);
 ot_hbm_tkx_2beat_tx_pr pt(clk,rst_n,boot_start,pr_raw,pb,ptf,ps);
 reg[1170:0]nc[0:LINK_STAGES-1],pc[0:LINK_STAGES-1];
 always@(posedge clk)begin nc[0]<=nb;pc[0]<=pb;for(integer j=1;j<LINK_STAGES;j++)begin nc[j]<=nc[j-1];pc[j]<=pc[j-1];end end
 ot_hbm_tkx_2beat_rx #(.LINK_STAGES(LINK_STAGES)) nr(clk,rst_n,boot_start,nc[LINK_STAGES-1],nq,nrf);
 ot_hbm_tkx_2beat_rx_pr #(.LINK_STAGES(LINK_STAGES)) pr(clk,rst_n,boot_start,pc[LINK_STAGES-1],pq,prf);
 reg[2340:0]history[0:3];integer epoch=0,edge_count=0,checked=0,issued=0;reg check=0;reg[31:0]rng=32'hbc12345;
 always@(posedge clk)begin
  history[0]<=nq;for(integer h=1;h<4;h++)history[h]<=history[h-1];
  #0.01;edge_count++;
  if(check)begin
   if(ntf||ptf||nrf||prf)$fatal(1,"PINREG_PHASE_FAULT edge=%0d native%0d/%0d pr%0d/%0d",edge_count,ntf,nrf,ptf,prf);
   if(pq!==history[$test$plusargs("BAD_PRICE")?2:3])$fatal(1,"PINREG_COHORT_MISMATCH edge=%0d",edge_count);
   if(ps!==ns)$fatal(1,"PINREG_INPUT_SLOT_PARITY edge=%0d",edge_count);
   checked++;
  end
 end
 task automatic step;@(negedge clk);endtask
 task automatic restart;
  begin
   check=0;rst_n=0;boot_start=0;raw=0;repeat(10)step();rst_n=1;repeat(5)step();boot_start=1;step();boot_start=0;repeat(30)step();check=1;
  end
 endtask
 initial begin
  if($test$plusargs("MUT_BANK"))force pt.u.u.g_banked_payload.phase_b[17]=1'b0;
  for(epoch=0;epoch<2;epoch++)begin
   restart();
   for(integer c=0;c<256;c++)begin
    for(integer w=0;w<73;w++)begin rng=(rng>>1)^((rng&1)?32'h80200003:32'h0);raw[32*w+:32]=rng;end
    raw[2336+:5]=rng[4:0];raw[2332+:9]=0;
    if(ps && c%4==0)begin raw[2332+:9]=9'h155;issued++;end
    step();
   end
  end
  if(issued==0||checked<500)$fatal(1,"NO_TRAFFIC checked%0d issued%0d",checked,issued);
  $display("TKX_PINREG PASS N=%0d checked=%0d issued=%0d native_extra4 II2 cold_warm2",LINK_STAGES,checked,issued);$finish;
 end
endmodule
