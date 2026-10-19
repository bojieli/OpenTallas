`timescale 1ns/1ps
// KV-HROOT-PEER 10-18: qkd_host_peer_root_mux_pl (HOST cluster child qkd_hr_core_peer) vs the UNCHANGED
// qkd_host_peer_root_mux, same inputs every cycle.
//  (1) every output except the local rank-0 coordinator RX port (coordinator_rx_valid[0] / coordinator_rx_data[0+:512])
//      must be identical in every cycle (4-state !==): the one-hot TX round robin / AND-OR data load is cycle-exact, and
//      local_tx_ready (the rank side) is unchanged;
//  (2) the words the coordinator accepts on RX[0] (valid && ready) must be the SAME sequence in both, the _pl one
//      lagging by at most one word (one registered cycle); at every async reset the common prefix must match and the
//      reference may be at most one word ahead (the word in the slice dies with the reset, as the reference
//      coordinator's copy does).
// Sources hold valid/data until their handshake (class9 valid/ready), advanced on the reference's handshakes (the
// claim is that those are identical). Headers are mostly legal; a few epochs drive random headers (root mux faults).
// -DQKD_HR_PE_PL_MUTANT: the slice corrupts one bit -> must FAIL.
module tb_hr_peer_pl;
 parameter integer NCYC=200000, SEED=1018;
 reg ck=0,por_n=0;
 reg prv=0;reg[511:0]prd=0;reg ptr=0;
 reg ltv=0;reg[511:0]ltd=0;reg lrr=0;
 reg[7:0]crr=0;reg[7:0]ctv=0;reg[4095:0]ctd=0;
 wire a_prr,b_prr,a_ptv,b_ptv,a_ltr,b_ltr,a_lrv,b_lrv,a_f,b_f;
 wire[511:0]a_ptd,b_ptd,a_lrd,b_lrd;wire[7:0]a_crv,b_crv,a_ctr,b_ctr;wire[4095:0]a_crd,b_crd;
 qkd_host_peer_root_mux ua(.ck(ck),.por_n(por_n),.physical_rx_valid(prv),.physical_rx_data(prd),.physical_rx_ready(a_prr),
  .physical_tx_valid(a_ptv),.physical_tx_data(a_ptd),.physical_tx_ready(ptr),.local_tx_valid(ltv),.local_tx_data(ltd),
  .local_tx_ready(a_ltr),.local_rx_valid(a_lrv),.local_rx_data(a_lrd),.local_rx_ready(lrr),.coordinator_rx_valid(a_crv),
  .coordinator_rx_data(a_crd),.coordinator_rx_ready(crr),.coordinator_tx_valid(ctv),.coordinator_tx_data(ctd),
  .coordinator_tx_ready(a_ctr),.fault(a_f));
 qkd_host_peer_root_mux_pl ub(.ck(ck),.por_n(por_n),.physical_rx_valid(prv),.physical_rx_data(prd),.physical_rx_ready(b_prr),
  .physical_tx_valid(b_ptv),.physical_tx_data(b_ptd),.physical_tx_ready(ptr),.local_tx_valid(ltv),.local_tx_data(ltd),
  .local_tx_ready(b_ltr),.local_rx_valid(b_lrv),.local_rx_data(b_lrd),.local_rx_ready(lrr),.coordinator_rx_valid(b_crv),
  .coordinator_rx_data(b_crd),.coordinator_rx_ready(crr),.coordinator_tx_valid(ctv),.coordinator_tx_data(ctd),
  .coordinator_tx_ready(b_ctr),.fault(b_f));
 // everything but RX[0]
 wire[6+512+512+512+7+3584+8:0]va={a_prr,a_ptv,a_ltr,a_lrv,a_f,a_ptd,a_lrd,a_crv[7:1],a_crd[4095:512],a_ctr};
 wire[6+512+512+512+7+3584+8:0]vb={b_prr,b_ptv,b_ltr,b_lrv,b_f,b_ptd,b_lrd,b_crv[7:1],b_crd[4095:512],b_ctr};
 reg[511:0]qa[$],qb[$];
 integer seed,cyc,k,mism=0,first_mism=-1,smis=0,first_smis=-1,resets=0,acc_a=0,acc_b=0,phys_tx=0,rank_tx=0,faults=0;
 integer legal=1,epoch_len=0,maxlag=0;reg hs_l;reg[7:0]hs_c;
 task automatic word(output reg[511:0]w);begin for(int j=0;j<16;j++)w[j*32+:32]=$random(seed);end endtask
 task automatic drain;begin
  while(qa.size()>0&&qb.size()>0)begin
   if(qa[0]!==qb[0])begin smis=smis+1;if(first_smis<0)first_smis=cyc;end
   void'(qa.pop_front());void'(qb.pop_front());
  end
 end endtask
 task automatic new_epoch;begin legal=($random(seed)&7)!=0;epoch_len=300+($random(seed)&16'h3ff);end endtask
 always #5 ck=~ck;
 initial begin
  seed=SEED;new_epoch;
  repeat(3)@(negedge ck);por_n=1;
  for(cyc=0;cyc<NCYC;cyc=cyc+1)begin
   @(negedge ck);
   // settle-time checks (inputs were set 1 ns after the previous posedge)
   if(va!==vb)begin mism=mism+1;if(first_mism<0)first_mism=cyc;end
   if(a_f)faults=faults+1;
   if(a_ptv&&ptr)phys_tx=phys_tx+1;
   if((a_ctr&ctv)!=0)rank_tx=rank_tx+1;
   if(a_crv[0]&&crr[0])begin qa.push_back(a_crd[511:0]);acc_a=acc_a+1;end
   if(b_crv[0]&&crr[0])begin qb.push_back(b_crd[511:0]);acc_b=acc_b+1;end
   drain;
   if(qa.size()>maxlag)maxlag=qa.size();
   if(qb.size()>0)begin smis=smis+1;if(first_smis<0)first_smis=cyc;void'(qb.pop_front());end   // _pl ahead: impossible
   // handshakes that the coming posedge performs (reference side; the claim is that they are identical)
   hs_l=ltv&&a_ltr;hs_c=ctv&a_ctr;
   @(posedge ck);#1;
   epoch_len=epoch_len-1;
   if(hs_l)ltv=0;
   ctv=ctv&~hs_c;
   if(epoch_len<=0)begin
    por_n=0;resets=resets+1;
    if(qa.size()>1)begin smis=smis+1;if(first_smis<0)first_smis=cyc;end
    qa.delete();qb.delete();
    ltv=0;ctv=0;#1;por_n=1;new_epoch;
   end
   if(!ltv&&($random(seed)&1))begin ltv=1;word(ltd);end
   for(k=0;k<8;k=k+1)if(!ctv[k]&&(($random(seed)&3)==0))begin
    reg[511:0]w;word(w);
    if(legal||($random(seed)&1))begin w[7]=1;w[10:8]=0;w[13:11]=3'(k);end
    ctv[k]=1;ctd[k*512+:512]=w;
   end
   prv=$random(seed);word(prd);
   if(legal||($random(seed)&1))begin prd[7]=0;prd[13:11]=0;prd[10:8]=3'(1+(($random(seed)&32'h7fffffff)%7));end
   ptr=$random(seed);lrr=$random(seed);
   crr=legal?(($random(seed)&3)!=0?8'hff:8'($random(seed))):8'($random(seed));
  end
  $display("HR_PEER_PL seed=%0d cycles=%0d resets=%0d rx0_ref=%0d rx0_pl=%0d max_ref_lead=%0d phys_tx=%0d rank_tx_hs=%0d fault_cycles=%0d out_mismatches=%0d first_out_mismatch=%0d rx0_stream_errs=%0d first_rx0_err=%0d %s",
   SEED,NCYC,resets,acc_a,acc_b,maxlag,phys_tx,rank_tx,faults,mism,first_mism,smis,first_smis,
   (mism==0&&smis==0&&maxlag<=1&&resets>=20&&acc_b>=10000&&phys_tx>=5000)?"PASS":"FAIL");
  $finish;
 end
endmodule
